# This file is part of the RomÃ©o model-checking software
# 
# Copyright University of Nantes, Ã‰cole Centrale de Nantes, IRCCyN
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

proc importFromOsate {c} {
   global nomRdP
   global tpn tabUnDo
   global modif
   global cheminFichiers
   global francais
   global tabPlace
   global tabTransition
   global nbProcesseur
   global fin ok destroy
   global simulatorOn
!   global romeoPath

    set executable $romeoPath
    append executable "bin/osate2romeo.exe"
 
 if {[file exists $executable]} {       
  
   if {$simulatorOn} {    
     affiche [mc "-Warning: Not allowed - Quit simulator first"]
   } else {
     set types {
      {{OSATE input file}     {.aaxl}  TEXT}
       }

     if {[fautIlSauver]==1} {
       set file [tk_getOpenFile -initialdir $cheminFichiers -filetypes $types -title "Import from OSATE (.aaxl)..."]
       if {[string compare $file ""]} {
         #*** souris en sablier
         $c configure -cursor watch
         update

	     affiche "\n"
	     affiche " -Importing $file from OSATE..."
	     exec $executable $file 
         set last [string first ".aaxl" $file] 
         if {$last>=0} {
           set nomRdP($tpn(onglet)) [string range $file 0 [expr $last -1]]  
           set ext ".xml"
           set nomRdP($tpn(onglet)) $nomRdP$ext
           #*** souris normal  (plus en sablier)***
           $c configure -cursor arrow
           update
           ouvrirPointXML .romeo.global $c 0 $nomRdP($tpn(onglet))
      }
     }
    }
   } 
  }	else { affiche "-Unable to import file - program osate2romeo not found!" }
}  




proc export2tina {c} {

global nomRdP
global tpn tabUnDo
global modif
global cheminFichiers
global francais

   set last [string first ".xml" $nomRdP($tpn(onglet))] 
    if {$last>=0} {
         set nomTina [string range $nomRdP($tpn(onglet)) 0 [expr $last -1]]  
    } else {
         set nomTina $nomRdP($tpn(onglet))
    }

    set types {
    {"TINA file"     {.ndr}      TEXT}
       }
       
    set ext ".ndr"

    if [string compare $nomTina "noName.xml"] {
        set fichier [tk_getSaveFile -filetypes $types  -title [mc "Export TPN to TINA as (file.ndr)"]\
	 -initialdir [repertoire $nomTina] -initialfile [nomSeul $nomTina$ext] -defaultextension .ndr]
    } else {
        set fichier [tk_getSaveFile -filetypes $types  -title [mc "Export TPN to TINA as (file.ndr)"]\
        -initialdir $cheminFichiers -initialfile $nomTina$ext -defaultextension .ndr]
    }

    if [string compare $fichier ""] {
       romeo2tina $fichier
    }
}


proc importFromTina {c} {
   global nomRdP
   global modif
   global tpn tabUnDo
   global cheminFichiers
   global francais
   global tabPlace
   global tabTansition
   global nbProcesseur
   global fin ok destroy
   global simulatorOn
   global tabConstraint
   global nbConstraints
   
 if {$simulatorOn} {    
   affiche [mc "-Warning: Not allowed - Quit simulator first"]
 } else {
   set types {
    {{TINA input file}     {.ndr}  TEXT}
       }
#  queCreerDetruirePTLPTF $c 0 0 0 0 0 0 0 0
  if {[fautIlSauver]==1} {
   set file [tk_getOpenFile -initialdir $cheminFichiers -filetypes $types -title [mc "Import from TINA..."]]
    if {[string compare $file ""]} {
       #*** souris en sablier
       $c configure -cursor watch
       update

       set last [string first ".ndr" $file] 
       if {$last>=0} {
          set nomRdP($tpn(onglet)) [string range $file 0 [expr $last -1]]  
          tina2romeo $file $c
          set modif($tpn(courant)) 1
          set ext ".xml"
          set nomRdP($tpn(onglet)) $nomRdP($tpn(onglet))$ext
#         .romeo.ligneDuBas.indication.nomRdp config -text [format [mc "TPN: %s"] $nomRdP]
       }
       #*** souris normal  (plus en sablier)***
       $c configure -cursor arrow
       update

    }
  }
 } 
}  


proc tina2romeo {fichier c} {
   global nomRdP
   global tpn tabUnDo
   global modif
   global home
   global cheminFichiers
   global francais
   global tabPlace
   global tabTransition
   global nbProcesseur
   global fin ok destroy
   global modif
   global maxX
   global maxY
   global infini
   global couleur
   global tabConstraint
   global nbConstraints
   
     affiche "\n"
#     affiche [format [mc "-Importing PN from TINA file: %s ..."] $fichier]
     affiche [mc "-Importing PN from TINA file: "]
     afficheBleu $fichier
     affiche " ..."

     set tabPlace($tpn(courant),1,statut) $fin
     set tabTransition($tpn(courant),1,statut) $fin
     set nbProcesseur 0
     set tabConstraint(0) ""
     set nbConstraints 1

     set file [open $fichier r]
#     set fileTina [read $file]
    while {([eof $file] <1)} {
       gets $file ligne     
       set balise [nextExpression $ligne " "]
       set ligne [supNextExpression $ligne " "]
       switch $balise { 
          p { 
             set x [nextExpression $ligne " "]
             set ligne [supNextExpression $ligne " "]   
             set y [nextExpression $ligne " "]
             set ligne [supNextExpression $ligne " "] 
             set label [nextExpression $ligne " "]
             set indice [supNextExpression $label "p"]
             set ligne [supNextExpression $ligne " "]
             set  mark [nextExpression $ligne " "]
             insererPlace $indice
             set tabPlace($tpn(courant),$indice,statut) $ok
             set tabPlace($tpn(courant),$indice,label,nom) $label
             set tabPlace($tpn(courant),$indice,label,dx) 10
             set tabPlace($tpn(courant),$indice,label,dy) 10
             set tabPlace($tpn(courant),$indice,processeur) 0
             set tabPlace($tpn(courant),$indice,priorite) 0
             set tabPlace($tpn(courant),$indice,jeton) $mark
             set tabPlace($tpn(courant),$indice,xy,x) $x
             set tabPlace($tpn(courant),$indice,xy,y) $y
          }
          t {
             set x [nextExpression $ligne " "]
             set ligne [supNextExpression $ligne " "]   
             set y [nextExpression $ligne " "]
             set ligne [supNextExpression $ligne " "] 
             set label [nextExpression $ligne " "]
             set indice [supNextExpression $label "t"]
             set ligne [supNextExpression $ligne " "]
             set alpha [nextExpression $ligne " "]
             set ligne [supNextExpression $ligne " "]
             set beta [nextExpression $ligne " "]
             if {$beta=="w"} {set beta $infini}
             insererTransition $indice
             set tabTransition($tpn(courant),$indice,statut) $ok
             set tabTransition($tpn(courant),$indice,dmin) $alpha
	         set tabTransition($tpn(courant),$indice,dmax) $beta
             set tabTransition($tpn(courant),$indice,label,nom) $label
             set tabTransition($tpn(courant),$indice,label,dx) 10
             set tabTransition($tpn(courant),$indice,label,dy) 10
             set tabTransition($tpn(courant),$indice,xy,x) $x
             set tabTransition($tpn(courant),$indice,xy,y) $y
          }
          e {
             if {[nextCar $ligne]=="p"} {
               set label [nextExpression $ligne " "]
               set indiceP [supNextExpression $label "p"]
               set ligne [supNextExpression $ligne "t"]          
               set indiceT [nextExpression $ligne " "]
               set ligne [supNextExpression $ligne " "]
               set ligne [supNextExpression $ligne " "]  
               set ligne [supNextExpression $ligne " "]  
               set weight [nextExpression $ligne " "]
               arcPlaceTransition $indiceP $indiceT 0 0 $weight PlaceTransition $couleur
            } else {
               set label [nextExpression $ligne " "]
               set indiceT [supNextExpression $label "t"]
               set ligne [supNextExpression $ligne "p"]          
               set indiceP [nextExpression $ligne " "]
               set ligne [supNextExpression $ligne " "]
               set ligne [supNextExpression $ligne " "]  
               set ligne [supNextExpression $ligne " "]  
               set weight [nextExpression $ligne " "]
               arcTransitionPlace $indiceP $indiceT 0 0 $weight $couleur
            }
          }  
          default {
         }
       }
    }
    close $file 
   redessinerRdP $c
   affiche [mc "done"]

}


proc supNextExpression {chaine separateur} {
 set resul ""
 if {[finLigne $chaine] ==0} {
    set firstPosition [string first $separateur $chaine]
    if {$firstPosition >=0} {set resul [string range $chaine [expr $firstPosition + [string length $separateur]] [string length $chaine] ]
    } else { set resul "" }
 }
 return $resul
}

proc nextExpression {chaine separateur} {
 set resul ""
 if {[finLigne $chaine] ==0} {
    set firstPosition [string first $separateur $chaine]
    if {$firstPosition >=0} {set resul [string range $chaine 0 [expr $firstPosition -1] ]
   } else { set resul $chaine }
 }
 return $resul
}

proc finLigne {chaine} {
set fin 1
for {set i 0} {[string index $chaine $i] != ""}   {incr i} {
   if {[string compare [string index $chaine $i] " "]!=0} {set fin 0}
 }
 return $fin
}


proc entier {chaine} {
 set resul 1
 if {[string compare $chaine ""]==0} {set resul 0}
 while {[string compare $chaine ""]} {
  if {[string first [nextCar $chaine] "0123456789"]<0} {set resul 0}
  set chaine [supNextCar $chaine]
 }
 return $resul
}

proc nextCar {chaine} {

 if {[string compare $chaine ""]} {
   return [string index $chaine 0]
 } else { return ""}

}

proc supNextCar {chaine} {
 if {[string compare $chaine ""]} {
  return [string range $chaine 1 [string length $chaine] ]
 } else {  return ""}
}


proc romeo2tina {fichier} {
global tabPlace tabTransition
global tpn tabUnDo
global nbProcesseur typePN
global fin ok
global modif
global infini

    if {$typePN==-2} {
	set scheduling 1
    } else {
	set scheduling 0
    }

 if [string compare $fichier ""] {
   affiche "\n"
#   affiche [format [mc "-exporting PN to TINA file: %s ..."] $fichier]
   affiche [mc "-Exporting PN to TINA file: "]
   afficheBleu $fichier
   affiche " ..."
   set File [open $fichier w]
    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
     if {$tabPlace($tpn(courant),$i,statut)==$ok} {
        puts $File "p $tabPlace($tpn(courant),$i,xy,x) $tabPlace($tpn(courant),$i,xy,y) p$i $tabPlace($tpn(courant),$i,jeton) n"
     }
    } 
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
     if {$tabTransition($tpn(courant),$i,statut)==$ok} {
        if {$tabTransition($tpn(courant),$i,dmax)==$infini} {
          set lft "w"
        } else {
          set lft $tabTransition($tpn(courant),$i,dmax)
        }
        puts $File "t $tabTransition($tpn(courant),$i,xy,x) $tabTransition($tpn(courant),$i,xy,y) t$i $tabTransition($tpn(courant),$i,dmin) $lft e"
     }
    }
   for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
     if {$tabTransition($tpn(courant),$i,statut)==$ok} {
        for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} {
          puts $File "e p$tabTransition($tpn(courant),$i,Porg,$j) 0 0 t$i 0 0 $tabTransition($tpn(courant),$i,PorgWeight,$j) n"
       }
        for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} {
          puts $File "e t$i 0 0 p$tabTransition($tpn(courant),$i,Pdes,$j) 0 0 $tabTransition($tpn(courant),$i,PdesWeight,$j) n"
        }
      }
   }
#   puts $File "h $fichier"
 
   close $File
   affiche [mc "done"]
  } else {
    affiche "\n"
    affiche [mc "-Export to TINA aborted"]
  }
}

proc ecrireChoix {fenetre} {
global modeRedu sizeOuReduTikz sizeOuReduSave

 set bascule $sizeOuReduTikz
 set sizeOuReduTikz $sizeOuReduSave
 set sizeOuReduSave $bascule

 if {$modeRedu==1} {
   $fenetre config -text [mc "       x size of LaTeX figure: "]
 } else {
   $fenetre config -text [mc "       reduction value (scale): "]
 }
}

proc export2tikz {c} {

global nomRdP
global tpn tabUnDo
global modif
global cheminFichiers
global francais
global nomTikz sizeOuReduTikz sizeOuReduSave
global modeRedu

   set sizeOuReduTikz 2
   set sizeOuReduSave 300
   set last [string first ".xml" $nomRdP($tpn(onglet))] 
    if {$last>=0} {
         set nomTikz [string range $nomRdP($tpn(onglet)) 0 [expr $last -1]]  
    } else {
         set nomTikz $nomRdP($tpn(onglet))
    }
  set ext ".tex"
  set nomTikz $nomTikz$ext
    
  wm withdraw .
  set fp .fenetreLatex
  catch {destroy $fp }
  toplevel $fp
  wm title $fp [mc "Export to LaTeX (Tikz)..."]

  frame $fp.dialogue
  pack $fp.dialogue -side top -fill both -expand yes
  set f $fp.dialogue


  frame $f.fileTex -bd 2 -relief sunken -bg white
  pack $f.fileTex -side top -fill both
  label $f.fileTex.lab
  pack $f.fileTex.lab -side left
  $f.fileTex.lab config -text [mc "LaTeX file: "]
  label $f.fileTex.nom -bg white
  pack $f.fileTex.nom -side left -fill both
  $f.fileTex.nom config -text "$nomTikz"

  frame $f.load -bd 2
  pack $f.load -side top -fill both
  button $f.load.open -text [mc "  Change LaTeX file  "] \
       -command "loadTikz $f"
  pack $f.load.open  -side left -expand 1   
  set modeRedu 1
  frame $f.taille
  pack $f.taille  -side top -expand 1   
  frame $f.taille.choix 
  pack $f.taille.choix  -side left -expand 1   
  radiobutton $f.taille.choix.a -text [mc "X size of the figure"] -variable modeRedu \
           -relief flat  -value 1  -width 22 -anchor w -selectcolor red -command "ecrireChoix $f.taille.size.label"
  radiobutton $f.taille.choix.b -text [mc "Reduction value"] -variable modeRedu \
           -relief flat  -value 2  -width 22 -anchor w -selectcolor red -command "ecrireChoix $f.taille.size.label"
  pack $f.taille.choix.a -side top -pady 2 -anchor w -fill x
  pack $f.taille.choix.b -side top -pady 2 -anchor w -fill x
  
  frame $f.taille.size -bd 2
  entry $f.taille.size.saisie -justify left -textvariable sizeOuReduTikz -relief sunken -width 10
  label $f.taille.size.label
  pack $f.taille.size.label -side left
  pack $f.taille.size.saisie -side left
  pack $f.taille.size -side right
  
  ecrireChoix $f.taille.size.label
 
  frame $fp.buttons
  pack $fp.buttons -side bottom -fill x -pady 2m
  button $fp.buttons.annuler -text [mc "Cancel"] -command  "destroy $fp"
  button $fp.buttons.accepter -default active -text [mc "Ok"]  \
      -command "validerTikz $fp"
  pack $fp.buttons.accepter $fp.buttons.annuler -side left -expand 1

  bind $fp <Return> "validerTikz $fp"
  bind $fp <<Echap>> "destroy $fp"

 proc validerTikz {fp} {
 global nomTikz sizeOuReduTikz sizeOuReduSave
 global modeRedu
   set x 200
   set x [format %f $sizeOuReduTikz]
# pour ne garder que les chiffres importants :
   set x [expr $x/1]
   destroy $fp
   if [string compare $nomTikz ""] {
        romeo2tikz $nomTikz $x $modeRedu
   }
 }
}

proc loadTikz {fp} {
 global nomTikz

  set types {
   {"LaTeX file"     {.tex}      TEXT}
       }
#  set file [tk_getOpenFile -initialfile $fichierBib -filetypes $types ]
set file [tk_getSaveFile -initialdir [repertoire $nomTikz] -initialfile [nomSeul $nomTikz] -filetypes $types -title [mc "Change LaTeX file name"]]
 if {[string compare $file ""]} {
   $fp.fileTex.nom config -text "$file"
   set nomTikz $file
 }
}



proc romeo2gastex {fichier Xsize mode} {
global tabPlace tabTransition
global tpn tabUnDo
global nbProcesseur typePN
global fin ok
global modif
global infini

    if {$typePN==-2} {
	set scheduling 1
    } else {
	set scheduling 0
    }
  set largeur [expr [tailleX]+50]
  set hauteur [expr [tailleY]+50]

  if {$mode==1} {
    if {$largeur>(2*$Xsize)} {
      set redu [expr $largeur/$Xsize]
    } else { 
      set redu 2
    }
  } else { 
    set redu $Xsize
    if {$redu < 1} {set redu 1}
  }
  set hauteur [format %2.1f [expr $hauteur/$redu]]
  set largeur [format %1.1f [expr $largeur/$redu]]
  set tailleP [format %1.1f [expr 20/$redu]]
  set tailleT [format %1.1f [expr 18/$redu]]
    
 if [string compare $fichier ""] {
   affiche "\n"
#   affiche [format [mc "-Exporting net to  file: %s ..."] $fichier]
   affiche [mc "-Exporting net to GasTeX file: "]
   afficheBleu "$fichier"
   affiche " ..."

   set File [open $fichier w]

    puts $File "% generated by romeo (IRCCyN) : a Tool for Time Petri Nets Analysis"

    puts $File "% \\usepackage\{gastex\}"

    if {$redu<=2} {
          puts $File "\\begin\{figure\} \n \{\\large \n \\begin\{center\}"
    } elseif {$redu < 3} {
          puts $File "\\begin\{figure\} \n \{\\normalsize \n \\begin\{center\}"
    } elseif {$redu < 4} {
          puts $File "\\begin\{figure\} \n \{\\footnotesize \n \\begin\{center\}"
    } elseif {$redu < 5} {
          puts $File "\\begin\{figure\} \n \{\\scriptsize \n \\begin\{center\}"
    } else {
          puts $File "\\begin\{figure\} \n \{\\tiny \n \\begin\{center\}"
    }   
    puts $File "\\begin\{picture\}($largeur,$hauteur)(30,-$hauteur)"

    puts $File "\% Places \n \\gasset\{Nw=$tailleP,Nh=$tailleP,Nmr=4,fillgray=1\} \n"
    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
     if {$tabPlace($tpn(courant),$i,statut)==$ok} {
       puts $File "\\gasset\{ExtNL=y,NLdist=[format %1.1f [expr 2/$redu]],NLangle=[nwse $tabPlace($tpn(courant),$i,label,dx) $tabPlace($tpn(courant),$i,label,dy)]\}"
       if {($scheduling==1)&&($tabPlace($tpn(courant),$i,processeur)>0)} {
          set lelabel "\\begin\{tabular\}\{l\}\$$tabPlace($tpn(courant),$i,label,nom)\$\\\\\$\\gamma=$tabPlace($tpn(courant),$i,processeur), \\omega=$tabPlace($tpn(courant),$i,priorite)\$\\end\{tabular\}"
       } else {
          set lelabel  "\$$tabPlace($tpn(courant),$i,label,nom)\$"
       }
       puts $File "\\node(P$i)([format %1.1f [expr $tabPlace($tpn(courant),$i,xy,x)/$redu]], -[format %1.1f [expr $tabPlace($tpn(courant),$i,xy,y)/$redu]]) \{$lelabel\}"
      }
    } 
  
    puts $File "\% Transitions \n \\gasset\{Nw=$tailleT,Nh=[expr $tailleT/5],Nmr=0,fillgray=0\} \n" 
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
     if {$tabTransition($tpn(courant),$i,statut)==$ok} {
     
        if {$tabTransition($tpn(courant),$i,dmax)==$infini} {
          set lft "\\infty\["
        } else {
          set lft "$tabTransition($tpn(courant),$i,dmax)\]"
        }
        puts $File "\\gasset\{ExtNL=y,NLdist=[format %1.1f [expr 4/$redu]],NLangle=[nwse $tabTransition($tpn(courant),$i,label,dx) $tabTransition($tpn(courant),$i,label,dy)]\}"
        
        if {$tabTransition($tpn(courant),$i,dmin)+$tabTransition($tpn(courant),$i,dmax)>0} {
          set leLabel "\\begin\{tabular\}\{l\}\$$tabTransition($tpn(courant),$i,label,nom)\$\\\\\$\[$tabTransition($tpn(courant),$i,dmin),$lft\$\\end\{tabular\}"
        } else { 
          set leLabel "\$$tabTransition($tpn(courant),$i,label,nom)\$"
        }

        puts $File "\\node(T$i)([format %1.1f [expr $tabTransition($tpn(courant),$i,xy,x)/$redu]],-[format %1.1f [expr $tabTransition($tpn(courant),$i,xy,y)/$redu]]) \{$leLabel\}"
     }
    }

   for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
     if {$tabTransition($tpn(courant),$i,statut)==$ok} {
        for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} {
          if {$tabTransition($tpn(courant),$i,PorgWeight,$j)>1} {set weight $tabTransition($tpn(courant),$i,PorgWeight,$j)} else {set weight ""}
          if {$tabTransition($tpn(courant),$i,PorgType,$j)==1} {set weight "\\phi"}
          if {$tabTransition($tpn(courant),$i,PorgNailx,$j)+$tabTransition($tpn(courant),$i,PorgNaily,$j)>0} {
             puts $File "\\drawqbedge(P$tabTransition($tpn(courant),$i,Porg,$j),[expr $tabTransition($tpn(courant),$i,PorgNailx,$j)/$redu],-[expr $tabTransition($tpn(courant),$i,PorgNaily,$j)/$redu],T$i)\{$weight\}"
          } else {
             puts $File "\\drawedge(P$tabTransition($tpn(courant),$i,Porg,$j),T$i)\{$weight\}"
          } 
        }
        for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} {
         if {$tabTransition($tpn(courant),$i,PdesWeight,$j)>1} {set weight $tabTransition($tpn(courant),$i,PdesWeight,$j)} else {set weight ""}

         if {$tabTransition($tpn(courant),$i,PdesNailx,$j)+$tabTransition($tpn(courant),$i,PdesNaily,$j)>0} {
           puts $File "\\drawqbedge(T$i,[format %1.1f [expr $tabTransition($tpn(courant),$i,PdesNailx,$j)/$redu]],-[format %1.1f [expr $tabTransition($tpn(courant),$i,PdesNaily,$j)/$redu]],P$tabTransition($tpn(courant),$i,Pdes,$j))\{$weight\}"
         } else {   
           puts $File "\\drawedge(T$i,P$tabTransition($tpn(courant),$i,Pdes,$j))\{$weight\}"
         }
        }
      }
   }
   
   
   puts $File "% Marquage \n \\gasset\{ExtNL=n,NLdist=0,NLangle=0\}"
   
   for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
     if {$tabPlace($tpn(courant),$i,statut)==$ok} {
        if {$tabPlace($tpn(courant),$i,jeton)>0} {
          puts $File "\\nodelabel(P$i)\{\$\\bullet\$\}"
        }
     }   
    } 
    
   puts $File "\\end\{picture\} \n \\end{center} \n \} \n \\caption{$fichier} \n \\label{fig-$fichier} \n \\end\{figure\}"

 
   close $File
   affiche [mc "done"]
  } else {
    affiche "\n"
    affiche [mc "-Export to GasTeX aborted"]
  }
}

proc nwse {x y} {
     if {($x>10) && ($y>10)} {
         return "-45"
      } elseif {($x>10) && ($y<-10)} {
         return "+45"
      } elseif {$x>10} {
         return "0"
      } elseif {($x< -10) && ($y>10)} {
         return "225"
      } elseif {($x<-10) && ($y<-10)} {
         return "135"
      } elseif {($x<-10)} {
         return "180"
      } elseif {($y>10)} {
         return "-90"
      } else {
         return "90"
      }
}

proc export2MarkG {c untimed} {

    global nomRdP typePN
    global tpn tabUnDo
    global cheminTemp plateforme
    global gpnU gpnK
    global romeoPath

    if {$typePN==-2} {
	set scheduling 1
    } else {
	set scheduling 0
    }   
 # option est egale ˆ "a" automaton ou "g" graph
    # UKH est egal ˆ u pour UPPAAL,  k pour KRONOS ou h pour Hytech
    set executable $romeoPath
    append executable "bin/gpn2"

    if {[string compare $plateforme "windows"]} {
	set fileExec $executable
    } else {
	set ext .exe
	set fileExec $executable$ext
    }
    
    if {[file exists $fileExec]} {   
     affiche "\n export $nomRdP($tpn(onglet)) to MarkG input format ..."
     if {$untimed ==1} {
 	    set lepid [exec $executable -mg $nomRdP($tpn(onglet)) > $cheminTemp/gpn.log &]
	 } else {
	   if {$scheduling==0} {
	    set lepid [exec $executable -mg -d $nomRdP($tpn(onglet)) > $cheminTemp/gpn.log &]
	   } else {
	    set lepid [exec $executable -mg -d -s $nomRdP($tpn(onglet)) > $cheminTemp/gpn.log &]
	   }
	 }  
	 set npid [lindex $lepid 0]
	 	afficheGpnLog $npid "$cheminTemp/gpn.log"
        affiche "pid = $npid ... done"
	 update
           
    } else { 
	affiche "\n"
	affiche [format [mc "-Unable to run %s - program not found!"] $executable]
    }

}

#------------------------------------------

proc romeo2tikz {fichier Xsize mode} {
global tabPlace tabTransition
global tpn tabUnDo
global nbProcesseur typePN
global fin ok
global modif
global infini
global allowedArc
global hideGU


  set largeur [expr [tailleX]+50]
  set hauteur [expr [tailleY]+50]

  if {$mode==1} {
    if {$largeur>(2*$Xsize)} {
      set redu [expr $largeur/$Xsize]
    } else { 
      set redu 1
    }
  } else { 
    set redu $Xsize
    if {$redu < 1} {set redu 1}
  }
  set hauteur [format %2.1f [expr $hauteur/$redu]]
  set largeur [format %1.1f [expr $largeur/$redu]]
  set tailleP [format %1.1f [expr 20/$redu]]
  set tailleT [format %1.1f [expr 18/$redu]]
    
    set redu  [expr $redu*1]
 if [string compare $fichier ""] {
   affiche "\n"
#   affiche [format [mc "-Exporting net to  file: %s ..."] $fichier]
   affiche [mc "-Exporting net to Tikz in latex file: "]
   afficheBleu "$fichier"
   affiche " ..."

   set File [open $fichier w]

    puts $File "% generated by romeo (IRCCyN) : a Tool for Time Petri Nets Analysis  \n"
    puts $File "\\documentclass\[a4paper,10pt\]\{article\}"
    puts $File "\\usepackage{tikz} \n \\usetikzlibrary{arrows,automata,positioning,petri}"
    puts $File "\n \n\\begin{document}"


    if {$redu<1} {
          puts $File "\\begin\{figure\} \n \{\\large \n \\begin\{center\}"
    } elseif {$redu < 2} {
          puts $File "\\begin\{figure\} \n \{\\normalsize \n \\begin\{center\} \n "
    } elseif {$redu < 3} {
          puts $File "\\begin\{figure\} \n \{\\footnotesize \n \\begin\{center\}"
    } elseif {$redu < 4} {
          puts $File "\\begin\{figure\} \n \{\\scriptsize \n \\begin\{center\}"
    } else {
          puts $File "\\begin\{figure\} \n \{\\tiny \n \\begin\{center\}"
    }   
#     set redu [expr $redu/1.5]
     puts $File "\\begin{tikzpicture} \n \[scale =1\] \n \\tikzset{node distance =[expr 2/$redu]cm, bend angle=-45,auto}"

     puts $File "\\tikzstyle\{place\}=\[circle,thick,draw=blue!75,fill=blue!20,minimum size=[format %1.1f [expr 20/$redu]] pt\]"
     puts $File "\\tikzstyle\{transition\}=\[rectangle,thick,draw=black!75,fill=black!20,minimum size=[format %1.1f [expr 18/$redu]] pt\]"


#    puts $File "\% Places \n \\gasset\{Nw=$tailleP,Nh=$tailleP,Nmr=4,fillgray=1\} \n"
    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
     if {$tabPlace($tpn(courant),$i,statut)==$ok} {
	 set lPpolaire [positionRelativePlace $i $redu]
	 puts $File "\\node \[place,tokens=$tabPlace($tpn(courant),$i,jeton)\](p$i) at ([format %1.1f [expr $tabPlace($tpn(courant),$i,xy,x)/$redu]] pt,-[format %1.1f [expr $tabPlace($tpn(courant),$i,xy,y)/$redu]] pt)\[label=\{\[label distance=[lindex $lPpolaire 0]pt\][lindex $lPpolaire 1]:$tabPlace($tpn(courant),$i,label,nom)\}\]\{\};"
#	 puts $File "\\node \[label\] at (p$i) \[xshift= [format %1.1f [expr $tabPlace($tpn(courant),$i,label,dx)*2/$redu]] pt,yshift= -[format %1.1f [expr $tabPlace($tpn(courant),$i,label,dy)*2/$redu]] pt\] \{$tabPlace($tpn(courant),$i,label,nom)\};"
   #ICI
      }
    } 
  
   for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
     if {$tabTransition($tpn(courant),$i,statut)==$ok} {
	 set lTpolaire [positionRelativeTrans $i label $redu]
 	 puts $File "\\node \[transition\] (t$i)  at ([format %1.1f [expr $tabTransition($tpn(courant),$i,xy,x)/$redu]] pt,-[format %1.1f [expr $tabTransition($tpn(courant),$i,xy,y)/$redu]] pt)\[label=\{\[label distance=[lindex $lTpolaire 0]pt\][lindex $lTpolaire 1]:\\begin\{tabular\}\{l\} $tabTransition($tpn(courant),$i,label,nom) \\\\  [intervalTex $i] \\end\{tabular\}\}\]\{\};"

	 if {!$hideGU(guard)} {
	 set lTpolaire [positionRelativeTrans $i guard $redu]
 	 puts $File "\\node \[transition\] (t$i)  at ([format %1.1f [expr $tabTransition($tpn(courant),$i,xy,x)/$redu]] pt,-[format %1.1f [expr $tabTransition($tpn(courant),$i,xy,y)/$redu]] pt)\[label=\{\[text=red,label distance=[lindex $lTpolaire 0]pt\][lindex $lTpolaire 1]:\\begin\{tabular\}\{l\} \$ $tabTransition($tpn(courant),$i,guard) \$ \\\\  \\end\{tabular\}\}\]\{\};"
	 }

	 if {!$hideGU(update)} {
	 set lTpolaire [positionRelativeTrans $i update $redu]
 	 puts $File "\\node \[transition\] (t$i)  at ([format %1.1f [expr $tabTransition($tpn(courant),$i,xy,x)/$redu]] pt,-[format %1.1f [expr $tabTransition($tpn(courant),$i,xy,y)/$redu]] pt)\[label=\{\[text=blue,label distance=[lindex $lTpolaire 0]pt\][lindex $lTpolaire 1]:\\begin\{tabular\}\{l\} \$ $tabTransition($tpn(courant),$i,update) \$ \\\\  \\end\{tabular\}\}\]\{\};"
	 }

	 if {$typePN==-3} {
	 set lTpolaire [positionRelativeTrans $i speed $redu]
	     puts $File "\\node \[transition\] (t$i)  at ([format %1.1f [expr $tabTransition($tpn(courant),$i,xy,x)/$redu]] pt,-[format %1.1f [expr $tabTransition($tpn(courant),$i,xy,y)/$redu]] pt)\[label=\{\[text=brown,label distance=[lindex $lTpolaire 0]pt\][lindex $lTpolaire 1]:\\begin\{tabular\}\{l\} \$ \\frac\{d\}\{dt\}=$tabTransition($tpn(courant),$i,speed) \$ \\\\  \\end\{tabular\}\}\]\{\};"
	 }


#	 puts $File "\\node \[label\] at (t$i) \[xshift= [format %1.1f [expr $tabTransition($tpn(courant),$i,label,dx)*2/$redu]] pt,yshift= -[format %1.1f [expr $tabTransition($tpn(courant),$i,label,dy)*2/$redu]] pt\] \{ \\begin\{tabular\}\{l\} $tabTransition($tpn(courant),$i,label,nom) \\\\  [intervalTex $i] \\end\{tabular\} \};"


     for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} {

	 if {$tabTransition($tpn(courant),$i,PorgWeight,$j)!=1} {
	     set weight  "node \{ $tabTransition($tpn(courant),$i,PorgWeight,$j)\}" 
	 } else {
	     set weight ""
	 }
         if {$tabTransition($tpn(courant),$i,PorgNailx,$j)+$tabTransition($tpn(courant),$i,PorgNaily,$j)>0} {
	      set lecontrole ".. controls ([format %1.1f [expr $tabTransition($tpn(courant),$i,PorgNailx,$j)/$redu]] pt,-[format %1.1f [expr $tabTransition($tpn(courant),$i,PorgNaily,$j)/$redu]] pt) .."
	 } else {
	      set lecontrole "edge"
	 }
	 if {($tabTransition($tpn(courant),$i,PorgType,$j)==4)&&($allowedArc(timedInhibitor)==1)} {
	      set laFleche "\[-o\]"

	 } elseif {($tabTransition($tpn(courant),$i,PorgType,$j)==3)&&($allowedArc(logicInhibitor)==1)} {
	      set laFleche "\[-*\]"

	 } elseif {($tabTransition($tpn(courant),$i,PorgType,$j)==2)&&($allowedArc(read)==1)} {
	      set laFleche "\[-open triangle 60 reversed\]"

 	 } elseif {($tabTransition($tpn(courant),$i,PorgType,$j)==1)&&($allowedArc(reset)==1)} {
	      set laFleche "\[-diamond\]"

	 } else {
	      set laFleche "\[-angle 45\]"
        }

	 puts $File "\\draw$laFleche (p$tabTransition($tpn(courant),$i,Porg,$j)) $lecontrole $weight (t$i) ;"


     }


  for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} {
	 if {$tabTransition($tpn(courant),$i,PdesWeight,$j)>1} {
	     set weight  "node \{ $tabTransition($tpn(courant),$i,PdesWeight,$j)\}" 
	 } else {
	     set weight ""
	 }
         if {$tabTransition($tpn(courant),$i,PdesNailx,$j)+$tabTransition($tpn(courant),$i,PdesNaily,$j)>0} {
	      set lecontrole ".. controls ([format %1.1f [expr $tabTransition($tpn(courant),$i,PdesNailx,$j)/$redu]] pt,-[format %1.1f [expr $tabTransition($tpn(courant),$i,PdesNaily,$j)/$redu]] pt) .."
	 } else {
	      set lecontrole "edge"
	 }
         set laFleche "\[-angle 45\]"
	 puts $File "\\draw$laFleche (t$i) $lecontrole $weight (p$tabTransition($tpn(courant),$i,Pdes,$j)) ;"
     }


    }
   }
 
#PRENDRE EN COMPTE LES ALLOWED ARC et FAIRE SCALE


   puts $File "\\end\{tikzpicture\} \n \\end{center} \n \} \n \\caption{$fichier} \n \\label{fig-$fichier} \n \\end\{figure\}"

   puts $File "\n \n\\end{document}"

   close $File
   affiche [mc "done"]
  } else {
    affiche "\n"
    affiche [mc "-Export to Tikz aborted"]
  }
}


proc positionRelativePlace {numPlace redu} { 
global tabPlace
global tpn tabUnDo
global fin ok parameters
global infini

    set lresul [polaire [expr $tabPlace($tpn(courant),$numPlace,label,dx)/$redu] [expr -$tabPlace($tpn(courant),$numPlace,label,dy)]/$redu]

    if {[lindex $lresul 1]>0} {
	set decal [expr 26/$redu]
    } else {
	set decal [expr 18/$redu]
    }

    return [lreplace $lresul 0 0 [format %1.1f [expr [lindex $lresul 0] - $decal]] ]
}

proc positionRelativeTrans {numTrans leChamp redu} { 
global tabTransition
global tpn tabUnDo
global fin ok parameters
global infini

    set lresul [polaire [expr $tabTransition($tpn(courant),$numTrans,$leChamp,dx)/$redu] [expr -$tabTransition($tpn(courant),$numTrans,$leChamp,dy)]/$redu]
    if {[lindex $lresul 1]>0} {
	set decal [expr 44/$redu]
    } else {
	set decal [expr 24/$redu]
    }

    return [lreplace $lresul 0 0 [format %1.1f [expr [lindex $lresul 0] - $decal]] ]

}


proc polaire {a b} { 

    set modu [expr hypot($a,$b)]
# sqrt($a*$a+$b*$b)
    set argu [expr (atan2($b, $a))*180/3.14]
    return [list [format %1.1f $modu] [format %1.1f $argu]]
}

proc intervalTex {i} { 
global tabTransition
global tpn tabUnDo
global fin ok parameters
global infini

if {$parameters < 1 } {
    set eft "\[$tabTransition($tpn(courant),$i,dmin)"
    if {$tabTransition($tpn(courant),$i,dmax)==$infini} { 
	set lft "\\infty\[" 
    } else { 
	set lft "$tabTransition($tpn(courant),$i,dmax)\]"
    } 
 } else {
    if {$tabTransition($tpn(courant),$i,minparam)==""} { 
	set eft "\[0" 
    } else { 
	set eft "\[$tabTransition($tpn(courant),$i,minparam)"
    }	
    if {$tabTransition($tpn(courant),$i,maxparam)==""} { 
	set lft "\\infty\[" 
    } else { 
	set lft "$tabTransition($tpn(courant),$i,maxparam)]"
    }	
 }
 return "\$ $eft,$lft \$"
}