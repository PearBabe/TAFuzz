# This file is part of the Roméo model-checking software
# 
# Copyright University of Nantes, École Centrale de Nantes, IRCCyN
# 
# Contributors: Olivier H. Roux (2000 -- 2020)
# 
# Olivier-h.Roux@ec-nantes.fr
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
#******************************************************************
# liens onglet tpn(courant) master et slave


proc calculTPNdeOnglet {leonglet} {
global tpn tabUnDo

	return [expr $leonglet*10000 + $tabUnDo([expr $leonglet*100],courant)]
}


proc calculTPNCourant {slave} {
global tpn tabUnDo
# set tpn(courant) [expr $tpn(onglet)*100 + $tabUnDo($tpn(onglet),courant)]
    if {$slave>0} {
	return [expr $tpn(onglet)*10000 + $slave*100 + $tabUnDo([expr $tpn(onglet)*100+$slave],courant)]
    } else {
	return [expr $tpn(onglet)*10000 + $tabUnDo([expr $tpn(onglet)*100],courant)]
    }
}


proc retrouverMasterSlaveFromCanvas {can} {
global tpn tabUnDo projet

set resultat 0
# set tpn(courant) [expr $tpn(onglet)*100 + $tabUnDo($tpn(onglet),courant)]

    if {$can==".romeo.global.frame.c"} {
	set resultat 0
    }	else {
	for {set i 1} {$i<=$projet($tpn(onglet),nbInput)}  {incr i} {
	    if {$can==".romeo.global.slave.slave$i.dessin.c"} {
		set resultat $i
	    }
	}
    }
    return $resultat
}


proc retrouverMasterSlaveFromNom {nom} {
global tpn projet

    set resultat 0

   for {set i 1} {$i<=$projet($tpn(onglet),nbInput)}  {incr i} {
	if {$projet($tpn(onglet),input,$i,status) != "deleted"} {
	    if {$nom==[sansXml $projet($tpn(onglet),input,$i,file)]} {
		set resultat $i
	    }
	}
   }
    return $resultat
}


# renvoie le numero du Slave ou 0
proc retrouverMasterSlave {} {
global tpn tabUnDo

# set tpn(courant) [expr $tpn(onglet)*100 + $tabUnDo($tpn(onglet),courant)]

	return [expr int(($tpn(courant)-$tpn(onglet)*10000)/100)]
}

#******************************************************************
# creation du canvas et des ascenceurs

proc canvasAsc {w c} {
    global maxX maxY zoom tpn tabUnDo projet viewOnglet
    global synchronized


    set deltaX 0
    set deltaY 0
    set zoom 1
    if {[winfo exists $w.frame]} {
#	$c xview moveto $deltaX
#	$c yview moveto $deltaY 
	#set deltaX [lindex [$c xview] 0]
	#set deltaY [lindex [$c yview] 0]
	destroy $c
	destroy $w.frame.vscroll
	destroy $w.frame.hscroll
	destroy $w.frame
    }
    frame $w.frame 
    pack $w.frame -side top -fill both -expand yes

    # rappel c = w.frame.c

    set reduireHauteur 1
    if {$projet($tpn(onglet),nbOpen)>0} {set reduireHauteur 2}

    set liste [list 0 0 [expr $maxX*$zoom] [expr $maxY*$zoom]]
    set hauteurecran [expr  [winfo screenheight $w]*1/(2*$reduireHauteur)]
    set largeurecran [expr  [winfo screenwidth $w]*1/2]
    canvas $c -scrollregion $liste -width $largeurecran -height $hauteurecran   \
	-relief sunken -borderwidth 2 \
	-xscrollcommand "$w.frame.hscroll set" \
	-yscrollcommand "$w.frame.vscroll set" 
    scrollbar $w.frame.vscroll -orient verti -command "$c yview"
    scrollbar $w.frame.hscroll -orient horiz -command "$c xview"

    $c xview moveto $viewOnglet(X,$tpn(onglet))
    $c yview moveto $viewOnglet(Y,$tpn(onglet))

#    pour mac OS et Windows
#   bind $c <MouseWheel> [subst {
#    if {%D > 0} {
#        zoomPlus $w $c
#    } else {
#        zoomMoins $w $c
#    }
    #   }]

    # Lz-e zoom avec les touches ctrl +-
    
    bind $c <Control-plus>  [subst { zoomPlus $w $c }]
    bind $c <Control-equal>  [subst { zoomPlus $w $c }]
    bind $c <Control-minus>  [subst {zoomMoins $w $c}]
    bind $c <Control-KP_Add> [subst { zoomPlus $w $c }]
    bind $c <Control-KP_Subtract>  [subst {zoomMoins $w $c}]

    # Le deplacement dans la fenetre complete (avec ascenceurs) avec le pad ou la souris
    
# Windows/macOS
    bind $c <MouseWheel> [list mouseWheelScroll $c %D %s]

proc mouseWheelScroll {w delta modifiers} {
    if {[string first "Shift" $modifiers] >= 0 || $modifiers == 1} {
        $w xview scroll [expr {($delta > 0) ? -3 : 3}] units
    } else {
        $w yview scroll [expr {($delta > 0) ? -3 : 3}] units
    }
}

# Linux
bind $c <Button-4> [list mouseButtonScroll $c -1 %s]
bind $c <Button-5> [list mouseButtonScroll $c +1 %s]

proc mouseButtonScroll {w delta modifiers} {
    if {[string first "Shift" $modifiers] >= 0 || $modifiers == 1} {
        $w xview scroll [expr {$delta < 0 ? -3 : 3}] units
    } else {
        $w yview scroll [expr {$delta < 0 ? -3 : 3}] units
    }
}

# Necessaire pour le ctrl +-
   focus $c
    
    # dessin des ascenceurs : 

    grid $c -in $w.frame \
	-row 0 -column 0 -rowspan 1 -columnspan 1 -sticky news
    grid $w.frame.vscroll \
	-row 0 -column 1 -rowspan 1 -columnspan 1 -sticky news
    grid $w.frame.hscroll \
	-row 1 -column 0 -rowspan 1 -columnspan 1 -sticky news
    grid rowconfig    $w.frame 0 -weight 1 -minsize 0
    grid columnconfig $w.frame 0 -weight 1 -minsize 0

    # ++++++ le fond blanc

    $c config -bg white
#$c xview moveto 0.5
    
    set font1 {Times 12}
    set font2 {Helvetica 24 bold}

#    $c xview moveto $deltaX
#    $c yview moveto $deltaY 

    set tpn(courant) [calculTPNCourant 0]
    redessinerRdP $c
#   queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0


    #******************Racourci commande + click sur la fenetre : creation

    bind $c <B1-Motion> "moveSurCanvas $c %x %y"
    bind $c <Button-1> "downSurCanvas $c %x %y 0"
    bind $c <ButtonRelease-1> "releaseSurCanvas $c %x %y"
    bind $c <Button-3> "clickDroitSurCanvas $c %x %y 0"
    bind $c <Button-2> "clickDroitSurCanvas $c %x %y 0"
    
}

#******************************************************************
# creation du canvas slave et des ascenceurs


proc slaveCanvas {w nbopenslave} {
   global maxX maxY zoom
    global synchronized projet tpn

    if {[winfo exists $w.slave]} {
	destroy $w.slave.hscroll
	destroy $w.slave.vscroll
	destroy $w.slave
	
    }
    frame $w.slave 
    pack $w.slave -side top -fill both -expand yes

    for {set i 1} {$i<=$projet($tpn(onglet),nbInput)}  {incr i} {
	if {$projet($tpn(onglet),input,$i,status) == "open"} {
	    set tpn(courant) [calculTPNCourant $i]
	    frame $w.slave.slave$i 
	    pack $w.slave.slave$i -side left -fill both -expand yes
#     label  $leProjet.projet.nomProjet.text   -bg gray90

	    frame $w.slave.slave$i.label
	    pack $w.slave.slave$i.label -side top -fill both -expand no
	    label $w.slave.slave$i.label.title  -text "$projet($tpn(onglet),input,$i,file)"
	    pack $w.slave.slave$i.label.title -side top -fill both -expand no
	    frame $w.slave.slave$i.dessin
	    pack $w.slave.slave$i.dessin -side top -fill both -expand yes
	    slavecanvasAsc $w.slave.slave$i.dessin $i $nbopenslave 
	}
    }
}
 
proc slavecanvasAsc {slave idSlave nb} {
    global maxX maxY zoom
    global synchronized

    set can $slave.c

    # rappel can = $w.frame.c

    if {$nb==0} {set nb 1}
    set liste [list 0 0 [expr $maxX*$zoom] [expr $maxY*$zoom]]
    set hauteurecran [expr  [winfo screenheight .romeo.global]*1/4]
    set largeurecran [expr  [winfo screenwidth .romeo.global]*1/( 2*$nb)]
    canvas $can -scrollregion $liste -width $largeurecran -height $hauteurecran  \
	-relief sunken -borderwidth 2 \
	-xscrollcommand "$slave.hscroll set" \
	-yscrollcommand "$slave.vscroll set" 
    scrollbar $slave.vscroll -command "$can yview" 
    scrollbar $slave.hscroll -orient horiz -command "$can xview" 

 
    # dessin des ascenceurs : 

    grid $can -in $slave \
	-row 0 -column 0 -rowspan 1 -columnspan 1 -sticky news
    grid $slave.vscroll \
	-row 0 -column 1 -rowspan 1 -columnspan 1 -sticky news
    grid $slave.hscroll \
	-row 1 -column 0 -rowspan 1 -columnspan 1 -sticky news
    grid rowconfig    $slave 0 -weight 1 -minsize 0
    grid columnconfig $slave 0 -weight 1 -minsize 0

    # ++++++ le fond blanc

    $can config -bg white
    $can xview moveto 0
   $can yview moveto 0
    set font1 {Times 12}
    set font2 {Helvetica 24 bold}

    redessinerRdP $can
  #  queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0
    #******************Racourci commande + click sur la fenetre : creation

    bind $can <B1-Motion> "moveSurCanvas $can %x %y"
    bind $can <Button-1> "downSurCanvas $can %x %y $idSlave"
    bind $can <ButtonRelease-1> "releaseSurCanvas $can %x %y"
    bind $can <Button-3> "clickDroitSurCanvas $can %x %y $idSlave"
    bind $can <Button-2> "clickDroitSurCanvas $can %x %y $idSlave"
    
}



#******************************************************************   IMPORTPN

 proc importPN {onglet nomTPN} {
     global projet cheminFichiers tpn nomRdP simulatorOn
    
  if {$simulatorOn==0} {
     set types {
	{"TPN file"     {.xml}      TEXT}
	{"Slave file"     {.sla}      TEXT}
     }

#     if {[file exists $projet($onglet,fichier$indice)]} {
#	     set repertoireInitial $projet($onglet,fichier$indice)
 #    } else {
#	     set repertoireInitial [repertoire $nomRdP($tpn(onglet))]
#     }

     set repertoireInitial [repertoire $nomRdP($tpn(onglet))]
     set file [tk_getOpenFile -initialdir $repertoireInitial -filetypes $types ]

     set nameFile  [nomSeul $file]

     if {[string compare $nameFile ""]} {

	 set existeDeja 0
	 for {set i 1} {$i<=$projet($onglet,nbInput)}  {incr i} { 
	     if {$projet($onglet,input,$i,file)==$nameFile} {set existeDeja 1}
	 }

	 if {$existeDeja==0} {
	     set projet($onglet,nbInput) [expr $projet($onglet,nbInput)+1]
	     set projet($onglet,input,$projet($onglet,nbInput),file) $nameFile
	     set projet($onglet,input,$projet($onglet,nbInput),status)  "closed"

     
	     set filetarget "$repertoireInitial\/$nameFile"
	     if { [repertoire $file] != $repertoireInitial} {
		 set ok [file copy $file $filetarget]
		 #puts "$repertoireInitial\/ $ok -> $file"
	     }	    

	     destroy .projet$onglet

	     ouvrirProjet $onglet $nomTPN


	     parserSlave $projet($onglet,nbInput)
#	 ouvrirPointXML .romeo.global .romeo.global.frame.c 1 $filetarget
	 
	 }

     }
  }
}

proc openInput {slave onglet} {
 global projet cheminFichiers tpn nomRdP


    if {$projet($onglet,nbOpen)<6} {

	set projet($onglet,input,$slave,status)  "open"
	set projet($onglet,nbOpen) [expr $projet($onglet,nbOpen)+1]

	redessinerProjet .romeo.global

	set boutonSlave .projet$onglet.projet.input.fichierPN.fichierPN$slave
	$boutonSlave.open  configure -state disabled
	$boutonSlave.close  configure -state normal
    }

#    destroy .projet$onglet
 #   ouvrirProjet $onglet $nomRdP($tpn(onglet)) 
}


proc closeInput {slave onglet} {
 global projet cheminFichiers tpn nomRdP

  if {$projet($onglet,nbOpen)>0} {
    set projet($onglet,input,$slave,status)  "closed"
     set projet($onglet,nbOpen) [expr $projet($onglet,nbOpen)-1]
    

## ATTENTION
    if {$projet($onglet,nbOpen)==0} {
	redessinerProjet .romeo.global
    } else {
	    destroy .romeo.global.slave.slave$slave
    }

    set boutonSlave .projet$onglet.projet.input.fichierPN.fichierPN$slave
    $boutonSlave.open  configure -state normal
    $boutonSlave.close  configure -state disabled

  }
#	 ouvrirProjet $onglet $nomRdP($tpn(onglet)) 
}







 proc removeInclude {indice onglet nomTPN} {
     global projet cheminFichiers tpn nomRdP simulatorOn
    
  if {$simulatorOn==0} {
    

     for {set i $indice} {$i<$projet($onglet,nbInclude)}  {incr i} { 
#	 puts "$i : $projet($onglet,include,$i) et --- $i+1  $projet($onglet,include,[expr $i+1])"
	      set projet($onglet,include,$i,file) $projet($onglet,include,[expr $i+1],file)
     }
     set projet($onglet,nbInclude) [expr $projet($onglet,nbInclude)-1]


     destroy .projet$onglet
     
     ouvrirProjet $onglet $nomTPN
 }
}

proc removeInput {slave onglet nomTPN} {
     global projet cheminFichiers tpn nomRdP simulatorOn
    
  if {$simulatorOn==0} {
    
#     for {set i $indice} {$i<$projet($onglet,nbInput)}  {incr i} { 
#	 set projet($onglet,input,$i)  $projet($onglet,input,[expr $i+1])
 #    }


     set projet($onglet,input,$slave,file) "deleted"

     if {$projet($onglet,input,$slave,status) == "open"} {
	 set projet($onglet,nbOpen) [expr $projet($onglet,nbOpen)-1]
	 set projet($onglet,input,$slave,status)  "deleted"

#	 if {$projet($onglet,nbOpen)<=1} {
	     redessinerProjet .romeo.global
#	 } else {
#	     destroy .romeo.global.slave.slave$slave
#	 }
     }

     set projet($onglet,input,$slave,status)  "deleted"

     destroy .projet$onglet
     
     ouvrirProjet $onglet $nomTPN
  }
 }


proc includeFile {onglet nomTPN} {
     global projet cheminFichiers tpn nomRdP simulatorOn
    
  if {$simulatorOn==0} {

   set types {
	{"c file"     {.c}      TEXT}
	{"text file"     {.txt}      TEXT}
     }


     set repertoireInitial [repertoire $nomRdP($tpn(onglet))]

     set file [tk_getOpenFile -initialdir  $repertoireInitial -filetypes $types ]
	    	    

     set nameFile  [nomSeul $file]

     if {[string compare $nameFile ""]} {

	 set existeDeja 0	
	 
	 for {set i 1} {$i<=$projet($onglet,nbInclude)}  {incr i} { 
	     if {$projet($onglet,include,$i,file)==$nameFile} {set existeDeja 1}
	 }

	 if {$existeDeja==0} {
	      set projet($onglet,nbInclude) [expr $projet($onglet,nbInclude)+1]
	      set projet($onglet,include,$projet($onglet,nbInclude),file) $nameFile
     
	     set filetarget "$repertoireInitial\/$nameFile"
	     if { [repertoire $file] != $repertoireInitial} {
		 set ok [file copy $file $filetarget]
		 #	     puts "$repertoireInitial\/ $ok -> $file"
	     }	    

	     destroy .projet$onglet
	     ouvrirProjet $onglet $nomTPN	  
	 } 
     }
  }
}



proc retirerStructure {lastring} {


    while {[string first "\{" $lastring >=0} {
	
	set parens  [regexp -inline -all {[\{\}]} $lastring]
	set balance 0
	set nbFermeture 0
	set change("\{")  1   ;# This technique saves an if-block :)
	set change("\}") -1

	set fin 0
	# fermeture recupere le nombre de fermetures d'acolade avant equilibre (ouverture = fermeture)
	foreach p $parens {
	    incr balance $change(\"$p\")
	    if {($balance==0)} {
		set fin 1
	    } else {
		if {($p=="\{")&&($fin==0)} {
		    incr nbFermeture
		}
	    }
	}

	set debutStruct [occurence $lastring 1 "\{"]
	set finStruct [occurence $lastring $nbFermeture "\}"]

	set avantStruct [string range $lastring 0 $debutStruct]
	set apresStruct [string range $lastring [expr $finStruct+1] [string length $lastring]]
	set remplaceStruct " 0 "
	set lastring $avantStruct$remplaceStruct$apresStruct
puts "****: $lastring"
    }
puts "$lastring"
    return $lastring

}


proc lireInitially {lastring} {

#recupere le contenu de initially

    set lastring [supNextExpression $lastring initially]
#expression regulière pour recupérer les ouverture et fermeture d'acolade 


    set parens  [regexp -inline -all {[\{\}]} $lastring]
    set balance 0
    set nbFermeture 0
    set change("\{")  1   ;# This technique saves an if-block :)
    set change("\}") -1

    set fin 0
# fermeture recupere le nombre de fermetures d'acolade avant equilibre (ouverture = fermeture)
    foreach p $parens {
	incr balance $change(\"$p\")
	if {($balance==0)} {
	    set fin 1
	} else {
	    if {($p=="\{")&&($fin==0)} {
		incr nbFermeture
	    }
	}
    }

    set debutIni [occurence $lastring 1 "\{"]

 
    set finIni [occurence $lastring $nbFermeture "\}"]
    return [string range $lastring [expr $debutIni+1] [expr $finIni-1]]

}

proc retirerInitially {chaine} {

#recupere le contenu de initially

    set lastring [supNextExpression $chaine initially]
#expression regulière pour recupérer les ouverture et fermeture d'acolade 


    set parens  [regexp -inline -all {[\{\}]} $lastring]
    set balance 0
    set nbFermeture 0
    set change("\{")  1   ;# This technique saves an if-block :)
    set change("\}") -1

    set fin 0
# fermeture recupere le nombre de fermetures d'acolade avant equilibre (ouverture = fermeture)
    foreach p $parens {
	incr balance $change(\"$p\")
	if {($balance==0)} {
	    set fin 1
	} else {
	    if {($p=="\{")&&($fin==0)} {
		incr nbFermeture
	    }
	}
    }

    set debutIni [occurence $chaine 1 initially]
    set ledebut [string range $chaine 0 [expr $debutIni-1]]

    set finIni [occurence $lastring $nbFermeture "\}"]
    set lafin [string range $lastring  [expr $finIni+1] [string length $lastring]]
    return "$ledebut$lafin"

}


proc reloadInput {slave onglet nomTPN} {
     global projet cheminFichiers tpn nomRdP simulatorOn
    
  if {$simulatorOn==0} {
    
      parserSlave $slave

      if {$projet($tpn(onglet),input,$slave,status) == "open"} {
	redessinerRdP .romeo.global.slave.slave$slave.dessin.c
      }
      
     destroy .projet$onglet
     
     ouvrirProjet $onglet $nomTPN
  }
 }
