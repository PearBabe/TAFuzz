# This file is part of the Rom√©o model-checking software
# 
# Copyright University of Nantes, √âcole Centrale de Nantes, IRCCyN
# 
# Contributors: Olivier H. Roux (2000 -- 2015)
# 
# Olivier-h.Roux@irccyn.ec-nantes.fr
# 
# This software is a computer program whose purpose is to [describe
# functionalities and technical features of your software].
# 
# This software is governed by the CeCILL license under French law and
# abiding by the rules of distribution of free software.  You can  use, 
# modify and/ or redistribute the software under the terms of the CeCILL
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info". 
# 
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability. 
# 
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or 
# data to be ensured and,  more generally, to use and operate it in the 
# same conditions as regards security. 
# 
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL license and that you accept its terms.
# 

 # procedure aide
# procedure imprime
# procedure quitter
# procedure aiguillageEnregistrer, enregistrerSous, enregistrerTpnXml
# procedure executerMercution...
# procedure compilerRDP, verifSem,
# procedure associer au lancement du calcul du GDC :
#          fautIlSauver, calculGDC, calculQuiGDC
# procedures diverses : tailleX, tailleY, sansEspace, slach, parcourir, repertoire, nomSeul



    # typePN : -1 : stopwatch ;   -2 scheduling ; 1 t-tpn ; 2 p-tpn


#+++++++++++++++++++++ LANCER CALCUL GRAPHE DES CLASSES  +++++++++++++++++++++++++++ 
 
#++++++++++++++++++++propose sauvegarde si le rdp a ete modifie+++++++++++ 
 
proc fautIlSauver {} { 
    global modif francais plateforme tpn
    global synchronized nomRdP

    if {$modif($tpn(courant)) ==1} { 
        set reponse [tk_messageBox -message [mc "Save $nomRdP($tpn(onglet)) ?"] -type yesnocancel -icon warning ] 
        switch -exact $reponse { 
            cancel { return 0 } 
            yes { aiguillageEnregistrer .romeo.global} 
            no {return 1} 
        } 
	# .romeo.global car w n'est pas passe en parametre 
    } 
    return 1 
} 
 
#***************************************************************************
#***************************** POUR les P-TPN  *****************************
#***************************************************************************

proc stateSpacePTPN {option} { 
    global nomRdP tpn
    global romeoPath
    global plateforme typePN
     
    set executable $romeoPath 
# Bon, pour le moment il n'y a qu'une option mais peut etre plus tard....
    if {$option ==1} {
	append executable "bin/mercutioGlop"
    } else {
	append executable "bin/mercutioGlop"
    }
#-----
	
    if {[string compare $plateforme "windows"]} { 
	  set fileExec $executable 
    } else { 
	  set ext .exe 
	  set fileExec $executable$ext 
    } 
 
    #  Quel est le nom du fichier qui sera genere par mercutio : 

    set last [string first ".xml" "$nomRdP($tpn(onglet))"] 
    set leslach [string last "/" $nomRdP($tpn(onglet))] 
    if {$leslach<0} {set leslach -1} 
    if {$last>=0} {set lachaine [string range "$nomRdP($tpn(onglet))" [expr $leslach+1] [expr $last -1]] 
    } else {set lachaine [string range "$nomRdP($tpn(onglet))" [expr $leslach+1] [length $nomRdP($tpn(onglet))]]} 
    set lachaine "$lachaine\-scg" 

    if {[file exists $fileExec]} {
	file delete $cheminTemp/mercutio.log 
	affiche "\n[mc "-Running:"]" 
 
	afficheMarron  " $executable $option $nomRdP($tpn(onglet))" 
	set lepid [exec $executable $option1 $option2 $fichier > $cheminTemp/mercutio.log &] 
        
 
        set npid [lindex $lepid 0] 
        affiche " ...pid = $npid" 
	afficheBackGround $lepid $lachaine 
    } else { 
  	  affiche "\n" 
	  affiche "-Unable to run $executable - program not found!"
    } 
} 


#***************************************************************************
#***************************** POUR les T-TPN  *****************************
#***************************************************************************


#++++++++++++++++++++ lancer gpn avec les bonnes options ++++++++++++++++++ 
 
proc calculGDC {option1 option2} { 
    global nomRdP tpn
    global home cheminTemp cheminFichiers cheminEditeur 
    global plateforme editAuto modif francais typePN parameters computOption
    global gpnU gpnK 
    global outFormat 
     
    # option1 = 0 OU pp en parameters OU in {d,p,x} en stopwatch (ou scheduling) pour {overapprox (donc DBM), polyedral, mixte} 
    # option2 in {m,g,a} pour {graphe des marquages, graphe des classes , automate (temporisÈ ou hybride)} 
 
    if {[string compare $option2 "a"]} { 
	  switch $outFormat(scg) { 
	    1 {set option3 -c} 
	    2 {set option3 -e} 
	    3 {set option3 -b} 
	  } 
    } else { 
      switch $outFormat(ta) { 
	    1 {set option3 -u} 
	    2 {set option3 -k}	     
	  }   
      if {$option1=="d"} {set option3 -y} 
    }  
     
    #integral parameters :
    if {($option1=="pp")&&($parameters>1)} {
	if {$computOption(hull)==1} {
	    set option1 pi
        } else {
	    set option1 pia
        }
    }
    set oui 1 
 
    if {$typePN==-2}  {if {[verifSem 1]==0} { set oui 0 } } 
    if {$oui} { set oui [fautIlSauver] } 
     
    set option2 -$option2 
    if {$oui==1} { 
	  genererOptionMercution "$nomRdP($tpn(onglet))" $option2 $option3 $option1  
    } else { 
      affiche "\n -computation aborted" 
    }   
} 
 
proc calculZBG {option1 option2} { 
    global nomRdP tpn
    global home cheminTemp cheminFichiers cheminEditeur 
    global plateforme editAuto modif francais  typePN
    global mercutioU mercutioK 
    global outFormat computOption 
 
    # option1 = 0 ou "l" si preserve ltl 
    # option2 0 ou "a" si ca gÈnÈre un automate 
     
    if {[string compare $option2 "a"]} { 
	  switch $outFormat(scg) { 
	    1 {set option2 -c} 
	    2 {set option2 -e} 
	    3 {set option2 -b} 
	  } 
     } else { 
      switch $outFormat(ta) { 
	    1 {set option2 -u} 
	    2 {set option2 -k} 
	 }   
    }  
     
    set oui 1 
 
    if {$typePN==-2}  {if {[verifSem 1]==0} { set oui 0 } } 
    if {$oui} { set oui [fautIlSauver] } 
     
    set option3 -z 
    if {$oui==1} { 
	  genererOptionMercution "$nomRdP($tpn(onglet))" $option3 $option2  $option1   
    } else { 
      affiche "\n -computation aborted" 
    }   
} 
 
proc genererOptionMercution {fichier option1 option2 option3} { 
    global  typePN computOption 
     
    if {$option3==0} { 
      set indiceOption 3 
    } else { 
      set indiceOption 4 
      set option3 -$option3  
    } 
     
    if {$option1 != "-m"} { 
      if {$typePN == -2} { 
         set option$indiceOption "-s" 
         incr indiceOption 
       } elseif {$typePN == -1} { 
         set option$indiceOption "-w" 
         incr indiceOption 
       }  
    } 
 
 set x 0 
 #OPTION MAXNODES
    if {[catch {set x [format %d $computOption(node)]} erreur]} { 
#       set computOption(node) 0 
       affiche "\n > error : $erreur - Stop condition ignored" 
    } elseif {$x>0} { 
       set option$indiceOption "--max-nodes=$x" 
       incr indiceOption 
    } 
    set x 0 
 #OPTION MAXTOKENS
    if {[catch {set x [format %d $computOption(token)]} erreur]} { 
       affiche "\n > error : $erreur - Stop condition ignored" 
    } elseif {$x>0 } { 
       set option$indiceOption "--max-tokens=$x" 
       incr indiceOption 
    } 
     
    if {$indiceOption==3} {  
       executerMercution $fichier $option1 $option2  
    } elseif {$indiceOption==4} {  
       executerMercution "$fichier" $option1 $option2 $option3 
    } elseif {$indiceOption==5} {  
       executerMercution "$fichier" $option1 $option2 $option3 $option4 
    } elseif {$indiceOption==6} {  
       executerMercution "$fichier" $option1 $option2 $option3 $option4 $option5 
    } elseif {$indiceOption==7} {  
       executerMercution "$fichier" $option1 $option2 $option3 $option4 $option5 $option6 
    }  
} 
 
proc executerMercution {fichier option1 option2 {option3 ""} {option4 ""} {option5 ""}} { 
    global nomRdP 
    global tpn tabUnDo 
    global cheminTemp plateforme 
    global  typePN computOption 
    global gpnU gpnK 
    global romeoPath 
 
    set executable $romeoPath 
    append executable "bin/mercutio" 
     
    if {[string compare $plateforme "windows"]} { 
	  set fileExec $executable 
    } else { 
	  set ext .exe 
	  set fileExec $executable$ext 
    } 
 
    set last [string first ".xml" "$nomRdP($tpn(onglet))"] 
    set leslach [string last "/" $nomRdP($tpn(onglet))] 
    if {$leslach<0} {set leslach -1} 
#  Quel est le nom du fichier qui sera genere par mercutio : 
    if {$last>=0} {set lachaine [string range "$nomRdP($tpn(onglet))" [expr $leslach+1] [expr $last -1]] 
    } else {set lachaine [string range "$nomRdP($tpn(onglet))" [expr $leslach+1] [length $nomRdP($tpn(onglet))]]} 
 
 
    if {$option1 != "-a"} { 
       if {$option1 == "-m"} { 
           set lachaine "$lachaine\-untimed" 
       } else {  
           if {($option3 =="-pp")||($option3 =="-pi")} { set lachaine  "$lachaine\$option3"} 
           if {$option1 == "-g"} {set lachaine "$lachaine\-scg"} 
           if {$option1 == "-z"} { 
             if {$option3 == "-l"} { 
                set lachaine "$lachaine\-zbg" 
             } else { 
                set lachaine "$lachaine\-ma" 
             } 
           } 
           if {$typePN <0} {  
              if {$option3 == "-d"} {set lachaine "$lachaine\-sd" 
              } elseif {$option3 == "-p"} {set lachaine "$lachaine\-sp" 
              }  elseif {$option3 == "-x"} {set lachaine "$lachaine\-sm" 
              } 
           } 
       } 
       if {$option2 == "-c"} {set lachaine "$lachaine\.txt" 
       } elseif {$option2 == "-b"} {set lachaine "$lachaine\.aut" 
       } elseif {$option2 == "-e"} {set lachaine "$lachaine\.mec"
       } elseif {$option2 == "-u"} {set lachaine "$lachaine\.xta" 
       } elseif {$option2 == "-k"} {set lachaine "$lachaine\.tg"} 
   } else { 
       if {$option2 == "-y"} {set lachaine "$lachaine\-scwa.hy" 
       } elseif {$option2 == "-u"} {set lachaine "$lachaine\-scta.xta" 
       } elseif {$option2 == "-k"} {set lachaine "$lachaine\-scta.tg"} 
   } 
 
 
# Executer mercutio : 
 
    if {[file exists $fileExec]} {        
	  file delete $cheminTemp/mercutio.log 
	  set ext ".xml" 
      affiche "\n[mc "-Running:"]" 
 
      if {$option3==""} { 
     	  afficheMarron  " $executable $option1 $option2 $fichier" 
  	      set lepid [exec $executable $option1 $option2 $fichier > $cheminTemp/mercutio.log &] 
      } elseif {$option4==""} { 
      	  afficheMarron  " $executable $option1 $option2 $option3 $fichier..." 
  	      set lepid [exec $executable $option1 $option2 $option3 $fichier > $cheminTemp/mercutio.log &]       
      } elseif {$option5==""} { 
      	  afficheMarron  " $executable $option1 $option2 $option3 $option4 $fichier..." 
  	      set lepid [exec $executable $option1 $option2 $option3 $option4 $fichier > $cheminTemp/mercutio.log &]       
      } else { 
      	  afficheMarron  " $executable $option1 $option2 $option3 $option4 $option5 $fichier..." 
  	      set lepid [exec $executable $option1 $option2 $option3 $option4 $option5 $fichier > $cheminTemp/mercutio.log &]       
      } 
 
	  set npid [lindex $lepid 0] 
	  affiche " ...pid = $npid" 
	  afficheBackGround $lepid $lachaine 
    } else { 
  	  affiche "\n" 
	  affiche "-Unable to run $fileExec - program not found!"
    } 
} 
 
 
 
 
proc existePid {npid} { 
    global cheminTemp plateforme 
    global  typePN 
    global gpnU gpnK 
    global romeoPath 
 
    set listePid [pid] 
} 
 
#++++++++++++++++++++ lancer gpn avec selection du fichier ++++++++++++++++++ 
 
proc calculQuoiGDC {option UPPouKRO} { 
    global nomRdP 
    global tpn tabUnDo 
    global home 
    global cheminFichiers 
    global cheminEditeur 
    global cheminTemp 
    global plateforme 
    global editAuto 
    global  typePN 
    global gpnU gpnK 
 
    # on regarde d'abord si on a deja ouvert un fichier ou pas 
    # ca donne le repertoire de depart 
 
    set types { 
	{{"fichier RdPT"}        {.xml}      TEXT} 
    } 
 
    if { [string compare "$nomRdP($tpn(onglet))" "noName.xml"]}  { 
        set fichier [tk_getOpenFile -filetypes $types -title [mc "Computing with input file:"] \
			 -initialdir [repertoire $nomRdP($tpn(onglet))] -initialfile [nomSeul $nomRdP($tpn(onglet))] -defaultextension .xml] 
    } else { 
        set fichier [tk_getOpenFile -filetypes $types  \
			 -initialdir $cheminFichiers -defaultextension .xml] 
    } 
    if [string compare $fichier ""] { 
	executerGpn $fichier $option $UPPouKRO 
    } 
} 
 
#++++++++++++++++++++ Polyedre Calcul exact ++++++++++++++++ 
 
proc calculPoly {op1 op3 op4} { 
    global cheminTemp plateforme 
    global  typePN nomRdP 
    global tpn tabUnDo 
    global outFormat 
    global romeoPath 
    set oui 1 
 
  if {$typePN==-2} { 
    if {[verifSem 1]==0} { set oui 0 } 
  } 
  if {$oui} { set oui [fautIlSauver] } 
 
  switch $outFormat(scg) { 
	1 {set op2 c} 
	2 {set op2 e} 
	3 {set op2 d} 
  } 
 
  if {$oui==1} { 
	set executable $romeoPath 
	append executable "bin/mercutio" 
	if {[string compare $plateforme "windows"]} { 
	    set fileExec $executable 
	} else { 
	    set ext .exe 
	    set fileExec $executable$ext 
	} 
	if {[file exists $fileExec]} {   
	    file delete $cheminTemp/gpn.log 
	    affiche "\n" 
	    affiche [format [mc "-Running: %s -%s -%s -%s %s ..."] $executable $op1 $op2 $op3 $op4 $nomRdP($tpn(onglet))] 
	    set lepid [exec $executable -$op1 -$op2 -$op3 -$op4 $nomRdP($tpn(onglet)) > $cheminTemp/gpn.log 2> $cheminTemp/gpnError.txt &]  
	    set npid [lindex $lepid 0] 
	    affiche "pid = $npid" 
	    afficheGpnLog $npid "$cheminTemp/gpn.log" 
	} else {  
	    affiche "\n" 
	    affiche "-Unable to run $fileExec - program not found!"
	} 
  } else { 
    affiche "\n -computation aborted" 
  }   
} 
 
 
 
# +++++++++++++++++++++++ MERCUTIO ++++++++++++++++++++++++++++++++++++++++++ 
proc calculMA {} { 
    global nomRdP 
    global tpn tabUnDo 
    global home cheminTemp cheminFichiers cheminEditeur 
    global plateforme editAuto modif francais  typePN 
    global mercutioU mercutioK 
    global outFormat 
 
    set oui 1 
 
    if {$typePN==-2}  {if {[verifSem 1]==0} { set oui 0 } } 
    if {$oui} { set oui [fautIlSauver] } 
 
  if {$oui==1} { 
 	  set last [string first ".xml" "$nomRdP($tpn(onglet))"] 
 
	  if {$last>=0} {set nomCompil [string range "$nomRdP($tpn(onglet))" 0 [expr $last -1]] 
	} else {set nomCompil $nomRdP($tpn(onglet))} 
 
	switch $outFormat(ta) { 
	    1 {set option u} 
	    2 {set option k} 
	}   
 
	if [string compare $nomCompil ""] { 
	    executerMercutio $nomCompil $option "" 
	} 
    } else { 
      affiche "\n -computation aborted" 
  }   
} 
 
proc calculZBGAncien {option} { 
    global nomRdP 
    global tpn tabUnDo 
    global home cheminTemp cheminFichiers cheminEditeur 
    global plateforme editAuto modif francais  typePN 
    global mercutioU mercutioK 
    global outFormat 
 
 set oui 1 
 if {$typePN==-2}  {if {[verifSem 1]==0} { set oui 0 } } 
 if {$oui} { set oui [fautIlSauver] } 
 
 if {$oui==1} { 
	 
	set last [string first ".xml" "$nomRdP($tpn(onglet))"] 
	if {$last>=0} {set nomCompil [string range "$nomRdP($tpn(onglet))" 0 [expr $last -1]] 
	} else {set nomCompil $nomRdP($tpn(onglet))} 
 
	switch $outFormat(scg) { 
	    # e = mec et a = aldebaran 
	    1 {set option2 e} 
	    2 {set option2 e} 
	    3 {set option2 d} 
	} 
	 
#	if [string compare $nomCompil ""] { 
#	    executerMercutio $nomCompil $option $option2 
#	} 
 
    if [string compare $nomCompil ""] { 
     if [string compare $option "l"] { 
        # pour un convergence par inclusion on enleve le -l : 
        set option $option2 
        set option2 "" 
     } 
     executerMercutio $nomCompil $option $option2 
   } 
 } else { 
   affiche "\n -computation aborted" 
 }   
} 
 
proc executerMercutio {fichier option1 option2} { 
    global cheminTemp plateforme 
    global  typePN 
    global mercutioU mercutioK 
    global romeoPath 
 
    set executable $romeoPath 
    append executable "bin/mercutio" 
     
    if {[string compare $plateforme "windows"]} { 
	set fileExec $executable 
    } else { 
	set ext .exe 
	set fileExec $executable$ext 
    } 
    if {[file exists $fileExec]} {        
	file delete $cheminTemp/mercutio.log 
	set ext ".xml" 
	if {$typePN > 0} { 
	    affiche "\n" 
	    if [string compare $option2 ""] { 
		#            affiche [format [mc "-Running:"] $executable -$option1 -$option2 $fichier$ext...] 
		affiche  "[mc "-Running:"] $executable -$option1 -$option2 $fichier$ext" 
		set lepid [exec $executable -$option1 -$option2 $fichier$ext > $cheminTemp/mercutio.log &] 
	    } else { 
		#             affiche [format [mc "-Running:"] $executable -$option1 $fichier$ext] 
		affiche  "[mc "-Running:"] $executable -$option1 $fichier$ext ..." 
		set lepid [exec $executable -$option1 $fichier$ext > $cheminTemp/mercutio.log &] 
	    }        
	    set npid [lindex $lepid 0] 
 
	    affiche "pid = $npid" 
	    afficheBackGround $lepid "" 
	    #       afficheGpnLog $npid "$cheminTemp/mercutio.log" 
	} 
    } else { 
	affiche "\n" 
	affiche "-Unable to run $fileExec - program not found!"
    } 
} 
 


#+++++++++++++++++++++ FIN CALCUL  +++++++++++++++++++++++++++ 
