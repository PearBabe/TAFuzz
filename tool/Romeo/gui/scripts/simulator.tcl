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

# Simulation du reseau de Petri TPN
#*********
#*
#procedure simulateProperty + Control Pannel
#*
# RAPPEL typePN :   -1 : stopwatch ;   -2 scheduling ; 1 t-tpn ; 2 p-tpn
#*********

# charge la bibliothèque partagée mercutio pour les calculs
global plateforme
global methode
global typePN

# GNAP   if {$typePN==-3} {set methode 2}

set methode 1
set simulator(mercutio) 0
set simulator(gpn) 0
set simulator(load) 0

proc firstLoad {} {
    global simulator
    global plateforme
    global nomSimul
    global cTPN_CurrentDomain cTPN_CurrentMarking
    global cTPN_FirableTransList cTPN_EnabledTransList cTPN_FirableColoredTwiceTransList  cTPN_FirableTransListPerColor
   global firingSequence firingSequenceTotal InitialToken
    global sepColor 

    set firingSequence [list]
    set cTPN_EnabledTransList [list]
    set cTPN_FirableTransList [list]
    set simulator(load) 1  
    set simulator(mercutio) 1
    set simulator(gpn) 1

    set cTPN_FirableColoredTwiceTransList [list]
    for {set uneCouleur 0} {$uneCouleur < 10} {incr uneCouleur} { # max 10 couleurs
	set cTPN_FirableTransListPerColor($uneCouleur) [list]
    }
    
}

proc afficheSimu {texte} {
    
    .fenetreSimul.dialogue.retour.text insert end  "$texte"
    .fenetreSimul.dialogue.retour.text yview moveto 1
}

proc afficheSimuColor {texte couleur} { 
    if {$couleur=="blue"} {
	afficheSimuBleu $texte
    } elseif {$couleur=="red"} {
	afficheSimuRouge $texte
    } elseif {$couleur=="green"} {
	afficheSimuVert $texte
    } elseif {$couleur=="brown"} { 
	afficheSimuBrown $texte
    } else {
	afficheSimuBackground $texte
    }
}  

proc afficheSimuBleu {texte} { 
    .fenetreSimul.dialogue.retour.text tag configure bleu -foreground blue
    .fenetreSimul.dialogue.retour.text insert end $texte bleu 
    .fenetreSimul.dialogue.retour.text yview moveto 1 
# update idletasks
}  

proc afficheSimuVert {texte} { 
    .fenetreSimul.dialogue.retour.text tag configure vert -foreground darkgreen
    .fenetreSimul.dialogue.retour.text insert end $texte vert 
    .fenetreSimul.dialogue.retour.text yview moveto 1 
# update idletasks
}  

proc afficheSimuRouge {texte} { 
    .fenetreSimul.dialogue.retour.text tag configure rouge -foreground red
    .fenetreSimul.dialogue.retour.text insert end $texte rouge 
    .fenetreSimul.dialogue.retour.text yview moveto 1 
# update idletasks
}  

proc afficheSimuBrown {texte} { 
    .fenetreSimul.dialogue.retour.text tag configure maron -foreground brown
    .fenetreSimul.dialogue.retour.text insert end $texte maron 
    .fenetreSimul.dialogue.retour.text yview moveto 1 
# update idletasks
}  

proc afficheSimuBackground {texte} { 
    .fenetreSimul.dialogue.retour.text tag configure autre  -background #c0d7ee
    .fenetreSimul.dialogue.retour.text insert end $texte autre 
    .fenetreSimul.dialogue.retour.text yview moveto 1 
# update idletasks
}
  

proc simulateTPN  {w c} {

    global firingSequence firingSequenceTotal nbTokenColor
    global nomRdP cheminTemp
    global francais
    global infini
    global scheduling parameters allowedArc outFormat typePN computOption
    global simulatorOn simulator
    global tabPlace InitialToken marquageCourant ok fin 
    global tpn tabUnDo
    global nomSimul
    global cTPN_CurrentDomain cTPN_CurrentMarking
    global cTPN_FirableTransList cTPN_EnabledTransList cTPN_FirableColoredTwiceTransList  cTPN_FirableTransListPerColor
    global modif methode typePN cost negcost 
    global uneSequence
    global correspondanceIndiceIdentifiant
    global afficheState
    global sepColor 


 

    initialiserCorrespIdIdentifier $tpn(courant)

    
    enregistrerMarquageInitial

# GNAP    if {$typePN==-3} {set methode 2}

   if {$typePN!=2} {
    
    set onSimule 1
    if {!$simulator(load)} {firstLoad}
    set cTPN_FirableColoredTwiceTransList {}

    #    if {($simulator(gpn))&&($scheduling)} { 
#	if {[catch {gpns_initPolka} ep]} { 
#	    affiche "\n " 
#	    affiche [format [mc ">error : %s"] $ep]
#	    set onSimule 0 
#	}
#    }  

    set etat(gpn) normal
    set etat(mercutio) normal
    
    if {$cost==0} {
	set etat(mercutio) normal
    } else {
	set etat(mercutio) disabled
	    set methode 2
    }


 #    if {$typePN==-3} {
#	set etat(mercutio) disabled
#	 set methode 2
 #    }

    
#    if {($simulator(gpn)+$simulator(mercutio))==1} {
#	if {$simulator(gpn)==1} { 
#	    set etat(mercutio) disabled
#	    set methode 2
#	} else { 
#	    set etat(gpn) disabled
#	    set methode 1
#	    if {($parameters>=1)||($typePN<0)} {set onSimule 0}
#	}
 #   } elseif {($simulator(gpn)+$simulator(mercutio))==0} {set onSimule 0}

    if {$typePN==-2} {
	set onSimule 0
	affiche "\n > Simulator not available in Scheduling mode"
    }


    if {$onSimule} { 
#	if {($modif($tpn(courant)) ==1)||(![string compare "$nomRdP($tpn(onglet))" "noName.xml"])} {
#	    set reponse [tk_messageBox -message [mc "Save net?"] -type yesno -icon question]
#	    switch -exact $reponse {
#		yes { 
#		    aiguillageEnregistrer .romeo.global
#		    if [string compare "$nomRdP($tpn(onglet))" "noName.xml"] {
 # 		        set nomSimul $nomRdP($tpn(onglet)) 
#		    } else {
#		        affiche "\n"
#		        affiche [mc "-Petri net not saved. Simulator will run with temporary file TPNSimul.xml"]
#		        set nomSimul "$cheminTemp/TPNSimul.xml"
#		        enregistrerTpnXml "$nomSimul" 0
#		    }               
#
#		}
#		no {
#		    affiche "\n"
#		    affiche [mc "-Petri net not saved. Simulator will run with temporary file TPNSimul.xml"]
#		    set nomSimul "$cheminTemp/TPNSimul.xml"
#		    enregistrerTpnXml "$nomSimul" 0
#		}
#	    }
#	} else {set nomSimul $nomRdP($tpn(onglet)) }
	set nomSimul $nomRdP($tpn(onglet)) 
	# ++++++++++++++++ Creation de la fenetre d'affichage ++++++++++++++++++
	
	affiche "\n"
	affiche [mc "-Opening \"Simulator\" window ... Starting simulator"]
	affiche " (working cts file: $cheminTemp/ctsfile.cts)"
	set fp .fenetreSimul
	toplevel $fp 

	wm protocol $fp WM_DELETE_WINDOW {"quitterSimulBrutalement"}
	wm title $fp [mc "TPN simulator"]
#	set x [expr [winfo rootx $c] + [winfo width $c]-10]
#	if {$x > ([winfo screenwidth $w]*3/4) } { set x [expr int([winfo screenwidth $w]*3/4)] }
#	set y [expr [winfo rooty $w] +1 ]
#	wm geometry $fp 40x40+$x+$y

	# Taille logique adaptÃ©e Ã  l'Ã©cran
	set size [expr {int(30 * [tk scaling])}]  

	# Position X
	set x [expr {int([winfo rootx $c] + [winfo width $c] - 10)}]
	set screen_w [winfo screenwidth $w]
	if {$x > int($screen_w*3/4)} { set x [expr {int($screen_w*3/4)}] }

	# Position Y
	set y [expr {int([winfo rooty $w] + 1)}]
	set screen_h [winfo screenheight $w]
	if {$y + $size > $screen_h} { set y [expr {$screen_h - $size - 1}]} 

	# GÃ©omÃ©trie avec entiers
	wm geometry $fp "${size}x${size}+${x}+${y}"



	
	frame $fp.dialogue 
	pack $fp.dialogue -side left -fill both -expand yes
	
	# message vers l'utilisateur
	frame $fp.dialogue.retour
	set f1 $fp.dialogue.retour
	pack $f1 -side top -fill both -expand yes
	
#	if {($parameters>=1)||($typePN<0)} {
#	    set methode 2
#	    set etat(gpn) disabled
#	    set etat(mercutio) disabled
#	} 

	frame $f1.ctrlSim 
	pack $f1.ctrlSim -expand no

	frame $f1.ctrlSim.method -bd 2
	pack $f1.ctrlSim.method -side top
	radiobutton $f1.ctrlSim.method.zone -text [mc "Zone-based method"] -font menufont -variable methode -value 1 -selectcolor red -command "reFaireSimu $c" -state $etat(mercutio)
	radiobutton $f1.ctrlSim.method.class -text [mc "State-class method"] -font menufont -variable methode -value 2 -selectcolor red -command "reFaireSimu $c" -state $etat(gpn)
	pack $f1.ctrlSim.method.zone -side top -pady 2 -anchor w
	pack $f1.ctrlSim.method.class -side top -pady 2 -anchor w


	frame $f1.ctrlSim.buttons -relief raised -bd 1
	button $f1.ctrlSim.buttons.reset -text [mc "Reset simulation"] -font menufont -command  "resetSimul $c"
	button $f1.ctrlSim.buttons.back -text "Step back" -font menufont -command "goBackSimulation $c"

	button $f1.ctrlSim.buttons.forward -text "Step Forward" -font menufont -command "goForwardSimulation $c"


	button $f1.ctrlSim.buttons.sequence -text "Play the sequence" -font menufont -command "playSequenceTransition" -font fontEditor
	pack $f1.ctrlSim.buttons -side top -fill both
	pack $f1.ctrlSim.buttons.reset $f1.ctrlSim.buttons.back $f1.ctrlSim.buttons.forward   -side left -expand 1


	frame $f1.seq -relief raised -bd 1
	frame $f1.seq.sequence 

	button $f1.seq.sequence.boutton -text "Simulate the sequence:" -font menufont -command "playSequenceTransition" -font fontEditor



    if {$cost > 0 } {
	frame $f1.ctrlSim.cost  -relief solid -bd 1
	pack $f1.ctrlSim.cost -side right -anchor w -expand yes
	checkbutton $f1.ctrlSim.cost.negative -text "Negative cost ?" -font menufont -variable negcost -selectcolor red
	pack $f1.ctrlSim.cost.negative -side top -anchor w -expand yes
    }



	entry $f1.seq.sequence.saisieNom -justify left -textvariable uneSequence -relief sunken -width 40 -bg white -font fontEditor
	pack $f1.seq.sequence.saisieNom -side right -fill both -expand yes
	pack $f1.seq.sequence.boutton -side left
	pack $f1.seq.sequence -side top -fill both
	label $f1.seq.label
	pack $f1.seq.label -side top
	$f1.seq.label config -text "Example of timed sequence: T1@10, T2@35 means -> firing T1 at date 10 and T2 at date 45" -font menufont

	pack $f1.seq -side top -fill both

	text $f1.text -yscrollcommand "$f1.vscroll set" -width 50 -height 20 -bg white -wrap word -font fontEditor
	scrollbar $f1.vscroll -command "$f1.text yview"
	pack $f1.text -side left -fill both -expand yes
	pack $f1.vscroll -side right -fill y
	
	# affichage des indices des Transitions
	frame $fp.indice -width 10 -height 10
	pack $fp.indice -side right -fill y
	afficheSimuIndice  $fp.indice
	
	frame $fp.dialogue.buttons -bd 2
	pack $fp.dialogue.buttons -side bottom -fill both

	frame $fp.dialogue.buttons.option
	pack $fp.dialogue.buttons.option -side left -anchor w
	checkbutton  $fp.dialogue.buttons.option.afficheEtat -text "Show all the state variables ?  " -font menufont -variable afficheState -selectcolor red 
# -command "changeTimedTrace $f"
	pack  $fp.dialogue.buttons.option.afficheEtat -side top -anchor w -expand yes

#	button $fp.dialogue.buttons.reset -text [mc "Reset simulation"] -command  "resetSimul $c"
	button $fp.dialogue.buttons.quit -text [mc "Quit Simulator"] -font menufont \
	    -command "editTPN $w $c"

#	pack $fp.dialogue.buttons.reset 
	pack $fp.dialogue.buttons.quit  -side left -expand 1

	boutonSimTPN $w $c
	set simulatorOn 1
	MAJdessinsProjetcourant $w
#	if {$typePN==-1} {
#			afficheSimu [mc "Stopwatch mode selected\n"]
#			affiche "\n"
#	} 
        if {$parameters>=1} {
			afficheSimu [mc "Parametric mode selected\n"]
			affiche "\n "
	}
	afficheSimu [mc "Color semantics (can be changed in preferences window):"]
	afficheSimu "\n "
	afficheSimu "-Enabled transitions -> "
	afficheSimuColor "brown " brown
	afficheSimu "\n "
	afficheSimu "-Firable transitions -> "
	afficheSimuColor "green " green
	afficheSimu "\n "
	afficheSimu [mc "Click on the transition to fire"]
	afficheSimu "\n "
	afficheSimu "-----------------------\n"
	if {$methode==1} {
			afficheSimu [mc "Initial zone:"]
	} else {
			afficheSimu [mc "Initial class:"]
	}
	afficheSimu "\n"
#	afficheSimu [printDomain $cSState]
	enregistrerMarquageCourant
        initSimulation

	MAJdessinsProjetcourant $w 
    } else { affiche " \n "
        affiche [mc "This simulator library has not been loaded"]
	}
  } else {
      affiche "\n"
      afficheRouge "-Simulation not available for P-TPN" 
  }
}

#++++++ procedures internes à simulate property


proc afficheSimuIndice {fi} {
   global firingSequence firingSequenceTotal 
    global tabTransition 
    global tpn tabUnDo
    global nomSimul
    global fin
    global ok
    global infini

    text $fi.text -yscrollcommand "$fi.vscroll set" -setgrid true \
	-width 10 -height 8 
    scrollbar $fi.vscroll -command "$fi.text yview"
    # -xscrollcommand "$fi.hscroll set"
    # scrollbar $fi.hscroll -orient horiz -command "$fi.text xview"


#    pack $fi.vscroll -side right -fill y
#    pack $fi.text -expand yes -fill both
    # pack $fi.hscroll -side bottom -fill x

#    $fi.text tag configure rouge -foreground red
#    $fi.text tag configure surgris -background #a0b7ce
#    $fi.text tag configure souligne -underline on


#    $fi.text insert end "  TRANSITION    \n" souligne
#    $fi.text insert end "Indice " surgris
#    $fi.text insert end "  \"label\" \n" rouge


    # transition par transition
#    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin} {incr i} {
#	if {$tabTransition($tpn(courant),$i,statut)==$ok} {
#	    $fi.text insert end "$i     " surgris
#	    $fi.text insert end "  \"$tabTransition($tpn(courant),$i,label,nom)\"\n" rouge
#	}
#    }
}

proc goBackSimulation {c} {
    global firingSequence firingSequenceTotal
    global methode parameters typePN
    global sepColor 

#puts "$firingSequence ------> [llength $firingSequence] -----> [lrange $firingSequence 0 [expr [llength $firingSequence] - 2] ] "
    if {[llength $firingSequence]>0} {

	set firingSequence [lrange $firingSequence 0 [expr [llength $firingSequence] - 2] ]

	afficheSimu "\n"
	afficheSimuColor "Step Back in the simulation \n" fondgris
	afficheSimuColor "Sequence from initial marking : $firingSequence \n" brown
	afficheSimu "-----------------------\n"
		if {$methode==1} {
		    afficheSimu "Zone:"
		} else {
		    afficheSimu "Class:"
		} 
		afficheSimu "\n"

	fireSequenceTransition $firingSequence
	MAJdessinsProjetcourant .romeo.global
    }
}

proc goForwardSimulation {c} {
    global firingSequence firingSequenceTotal
    global methode parameters typePN
    global sepColor 

    #puts "$firingSequence ------> [llength $firingSequence] -----> [lrange $firingSequence 0 [expr [llength $firingSequence] - 2] ] "
    

    if {[llength $firingSequenceTotal]>[llength $firingSequence]} {

	lappend firingSequence [lindex $firingSequenceTotal  [llength $firingSequence]]
	
	afficheSimu "\n"
	afficheSimuColor "Step Back in the simulation \n" fondgris
	afficheSimuColor "Sequence from initial marking : $firingSequence \n" brown
	afficheSimu "-----------------------\n"
		if {$methode==1} {
		    afficheSimu "Zone:"
		} else {
		    afficheSimu "Class:"
		} 
		afficheSimu "\n"

	fireSequenceTransition $firingSequence
	MAJdessinsProjetcourant .romeo.global
    }
}

proc reFaireSimu {c} {
   global firingSequence firingSequenceTotal 
    global methode parameters typePN

    if {$methode==1} {set zoneClass "Zone"} else {set zoneClass "Class"}
    afficheSimu "\n"
    afficheSimuColor "Replaying the simulation with $zoneClass based method\n" fondgris
    afficheSimuColor "Sequence from initial marking : $firingSequence\n" brown
    afficheSimu "-----------------------\n"
    afficheSimu "$zoneClass:\n"
    fireSequenceTransition $firingSequence
    MAJdessinsProjetcourant .romeo.global

}


#++++++++++++++++++
proc simulatorFireTranstion {c i slave} {
    global firingSequence firingSequenceTotal 
    global tabTransition 
    global tpn tabUnDo projet
    global tabPlace InitialToken 
    global ok fin
    global nomSimul
    global cTPN_CurrentDomain cTPN_CurrentMarking
    global cTPN_FirableTransList cTPN_EnabledTransList cTPN_FirableColoredTwiceTransList  cTPN_FirableTransListPerColor
    global methode parameters typePN
    global sepColor 


    set leTPN [calculTPNCourant $slave]
    set underscore "_"
    set doublePoint "::"
    
    if {$slave>0} { 
	set nomTransition "[sansXml $projet($tpn(onglet),input,$slave,file)]$doublePoint$tabTransition($leTPN,$i,id)" 
    } else {
	set nomTransition $tabTransition($leTPN,$i,id)
    }
    
    if {[firableTwice $slave$underscore$i]} {
	simulatorFireColoredTransition $c $nomTransition $slave$underscore$i
    } elseif {[firable $slave$underscore$i]} {
	set laCouleur [coloredFirableOnce $slave$underscore$i]
	if {$laCouleur>=0} {
	    simulatorAfficheEtfireLaSequencefiring $nomTransition$sepColor$laCouleur 
	} else {
	    simulatorAfficheEtfireLaSequencefiring $nomTransition 
	}

    } else {
		afficheSimu [format [mc ">Warning: Transition %s is not fireable"] $nomTransition]
		afficheSimu "\n"
    }
}  


proc   simulatorAfficheEtfireLaSequencefiring {nomTransition} {
   global firingSequence firingSequenceTotal
     global methode
     global sepColor 

    afficheSimu "\n"

    afficheSimuColor "Firing $nomTransition \n" fondgris 

    lappend firingSequence "$nomTransition"
    set firingSequenceTotal $firingSequence
    afficheSimuColor "Sequence from initial marking : $firingSequence" brown

    afficheSimu "\n"
    #mise à jour du réseau version C
    afficheSimu "-----------------------\n"
    if {$methode==1} {
	afficheSimu [mc "Zone:"]
    } else {
	afficheSimu [mc "Class:"]
    } 
    afficheSimu "\n"
    fireSequenceTransition $firingSequence
    
    MAJdessinsProjetcourant .romeo.global
}

proc simulatorFireColoredTransition {c nomTransition idTrans} {
    global plot
    global tabTransition tabPlace 
    global tpn tabUnDo
    global modif
    global francais
    global maxX maxY zoom
    global tabFlechePT tabFlecheTP tabNoeud
    global fin
    global nouveauWeight nouveauTokenColor
    global simulatorOn semaphore
    global couleurCourante tabColor resultatCouleur couleurPN nbTokenColor
    global methode
    global cTPN_FirableTransList cTPN_EnabledTransList cTPN_FirableColoredTwiceTransList  cTPN_FirableTransListPerColor
    global sepColor 

    
    set f .fenetreColorChoice
    catch {destroy $f}
    toplevel $f
	
    label $f.nom -bd 2
    pack $f.nom -side top -fill x -pady 2m
	
    $f.nom config -text "Firing $nomTransition : Color choice"
	

    frame $f.tokencolor -bd 2 
    pack $f.tokencolor -side top -fill x -pady 2m

    for {set uneCouleur 0} {$uneCouleur < $nbTokenColor($tpn(courant))} {incr uneCouleur} {

	if {[lsearch  $cTPN_FirableTransListPerColor($uneCouleur) $idTrans]>=0} {
	    
	    radiobutton $f.tokencolor.couleur$uneCouleur -text "Color $uneCouleur" -font menufont -variable nouveauTokenColor -value $uneCouleur -selectcolor red  -command "validerColoredFiring $f $uneCouleur $nomTransition"
	    pack $f.tokencolor.couleur$uneCouleur -side top -pady 2 -anchor w
        }
    }

#	puts "$nomTransition - $uneCouleur -> $cTPN_FirableTransListPerColor($uneCouleur) et cTPN_FirableColoredTwiceTransList "
	    
    bind $f <Return> "validerColoredFiring $f $nouveauTokenColor  $nomTransition"
    bind $f <Escape> "destroy $f"
 
    #++++++ procedures internes à doubleClickArc
    
    proc validerColoredFiring {f indice nomTransition} {
	global nouveauWeight nouveauTokenColor
	global tabTransition 
	global tpn tabUnDo
	global modif
	global resultatCouleur couleurCourante couleurPN
	global sepColor 
	
	simulatorAfficheEtfireLaSequencefiring $nomTransition$sepColor$indice

	destroy $f
#	redessinerRdP $c
    }
}


#--------------- A LA PLACE DE LA LIBRAIRIE 
#proc fireSequenceTransition  {laSequence} {
#   global nomRdP tpn
#   global cheminTemp simulOption
#   global romeoPath
#    global nomSimul
#   global cSStatesimulOption
#   global cTPN_CurrentDomain cTPN_CurrentMarking
#   global cTPN_FirableTransList cTPN_EnabledTransList cTPN_FirableColoredTwiceTransList  cTPN_FirableTransListPerColor

#    set executable $romeoPath
#    append executable "bin/mercutio-sim"
#    set sequenceTir "$cheminTemp/sequence.txt"

#    set File [open $sequenceTir w] 
#    puts $File $laSequence
#    close $File 
#    set reponse "$cheminTemp/simul.txt"

#    file delete -force $reponse
#    if {[file exists $executable]==1} {
#	if { [catch {exec $executable $simulOption(1) $simulOption(2) -v $nomSimul < $sequenceTir > $reponse}  erreur] ==0 } {

	# liste de transitions sensibilisées


#       getCurrentState $reponse
##	set cTPN_EnabledTransList [getEnabledTransitions $reponse]
##	set cTPN_FirableTransList [getFirableTransitions $reponse]
 
#    } else {
#	afficheSimu "error while executing :  $executable $simulOption(1) $simulOption(2) -v $nomSimul < $sequenceTir > $reponse \n $erreur"
#    }
#    } }

proc playSequenceTransition  {} {
    global uneSequence
    global methode
   global firingSequence firingSequenceTotal 
    global sepColor 


    if {$methode==1} {set zoneClass "Zone"} else {set zoneClass "Class"}
    afficheSimu "\n"
 
# ici il faudra vérifier que c'est bien une sequence de transitions

    afficheSimuColor "Restarting simulation with initial marking and initial $zoneClass:\n" fondgris
    initSimulation
	afficheSimuColor "Firing the sequence : $uneSequence  \n" fondgris


    if {$uneSequence== ""} {
	fireSequenceTransition " "
    } else {
	fireSequenceTransition $uneSequence
    }
    set firingSequence $uneSequence
    MAJdessinsProjetcourant .romeo.global
}

proc fireSequenceTransition  {laSequence} {
    global nomRdP tpn nomCheck modif useReduc 
    global tabPlace InitialToken marquageCourant ok fin 
    global tpn tabUnDo 
    global cost negcost
    global cheminTemp computOption
    global romeoPath  methode
    global parameters typePN computOption
    global plateforme
    global correspondanceIdIdentifier
    global sepColor 

    
#    puts "$tpn(courant) on fire $laSequence "
    set tpn(courant) [calculTPNCourant 0]
    set useReduc 0

# Pour que ca marche avec une liste avec ou sans virgules 
    set laSequence [retirerListeSeparateur $laSequence  [list ","]]
    set laSequence [join $laSequence ", "]

    file delete $cheminTemp/simulError.log
    set executable $romeoPath
    append executable "bin/romeo-cli"
    if {[string compare $plateforme "windows"]==0} {
	append executable ".exe"
    }
    set reponse "$cheminTemp/simul.ans"
    set syntaxerror "$cheminTemp/simulError.log"
    set ctsfile "$cheminTemp/ctsfile.cts"

    affiche "\n" 

    set opzone ""
   
   if {($cost==0)||($methode==1)} {
       if {$methode==1} {set opzone "zones,"}
       if {$parameters == 3 } {
	   set opzone "\[$opzone ihc\]"
       } elseif {$parameters == 2 } {
	   
	   if {$useReduc == 1 } {
	       set opzone "\[$opzone ip\]"
	   } else {
	       set opzone "\[$opzone ip, nored\]"
	   }
       } else {
	   if {$methode==1} {set opzone "\[zones\]"}
#	   if {$typePN==-3} {set opzone ""}
       }
    
       set simulation "simulate$opzone $laSequence"

   } else { # COST COST COST en classe

        set optionCost ""
        if {$negcost==1} {set optionCost ",neg_costs"}
	if {$cost==1} { set optionCost "cost_mode=poly$optionCost"}
	if {$cost==2} { set optionCost "cost_mode=split$optionCost"}
	if {$cost==3} { set optionCost "cost_mode=split$optionCost"}
	if {$cost==4} { set optionCost "cost_mode=global$optionCost"}


	
	if {$parameters == 3 } {
	     set optionCost "$optionCost,ihc"	
    } elseif {$parameters == 2 } {
	     set optionCost "$optionCost,ip"		
    }
	set simulation "simulate\[$optionCost\] $laSequence"

    }


    
    affiche "-Invoking romeo-cli : "
    afficheBleu "$simulation"
  #  set CTSSequence [calculSequenceCTS $simulation]

#    set nomDeBase [sansXml $nomRdP($tpn(onglet))]

# remettre marquage initial
    enregistrerMarquageCourant
    remettreMarquage 1
    export2CTS $tpn(courant) $ctsfile $simulation 0

# remettre marquage courant
    remettreMarquage 0


#   for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
#	if {$tabPlace($tpn(courant),$i,statut)==$ok} {
#	    set   tabPlace($tpn(courant),$i,jeton) 
#	    set tabPlace($tpn(courant),$i,jeton) $tabJetonProvisoire($i)
#	}
 #   }

#puts  $ctsfile 

#puts "+++++++++++++++++++++++++++++"
#puts $CTSSequence
    if { [catch {exec $executable -m $ctsfile > $reponse 2> $syntaxerror} erreur] } {

      if {![file exists $syntaxerror]} {
	    set File [open $syntaxerror w]
	    puts $File "$erreur"
	    close $File
	  }
    }

#  set glop "$executable $ctsfile"
#  exec $glop
#puts $reponse
    if {[emptyFile $syntaxerror]} {
       getCurrentState $reponse
    } else { 

	set file [open $syntaxerror r]
        afficheSimuColor "Stopping simulation\n" fondgris
	while {![eof $file]} {
	    gets $file line
	    if {[string compare  [nextExpression $line " "] "\[error\]"]==0} {
		set lineNumber [nextExpression [supNextExpression $line "Line "] ":"]
		if {$lineNumber != ""} {
		    set messageErreur [export2CTSgetError $tpn(courant) "" "" $lineNumber 0]
		    set localLineNumber [nextExpression [supNextExpression $messageErreur "(line "] "):"]
		    afficheSimuColor "[nextExpression $messageErreur "@@details**"]" red
		    afficheSimuColor "Line $lineNumber in CTS file: $ctsfile \n" blue
		    afficheSimuColor "[supNextExpression $line ":"] \n" blue
		    if {[sansEspace $localLineNumber]!=""} {
			afficheSimuColor "[arroundError $localLineNumber [supNextExpression $messageErreur "@@details**"]] \n" green
		    } else {
			afficheSimuColor "[arroundErrorFromCTS $lineNumber $ctsfile] \n" green
		    }
		} else {
		    afficheSimuColor "$line \n" red
		    afficheSimuColor "in CTS file: $ctsfile \n" blue
		}
	    } else {
		afficheSimuColor "$line \n" blue
#		afficheSimuColor "in CTS file: $ctsfile \n" blue
	    }
	}
	raise .fenetreSimul
	close $file
    }

    update idletasks
}

#--------------------------------------------------------------------------------------------
# remplacer labelTransition par labelTransition'Ti
#--------------------------------------------------------------------------------------------



proc getCurrentState {fichier} {
   global tabPlace InitialToken ok fin 
   global tpn tabUnDo nbTokenColor
   global cTPN_CurrentDomain cTPN_CurrentMarking
   global cTPN_FirableTransList cTPN_EnabledTransList cTPN_FirableColoredTwiceTransList  cTPN_FirableTransListPerColor
   global correspondanceIndiceIdentifiant
   global afficheState
   global sepColor 

    #  set fichier "adetruire.txt"

    set doublepoint "::"
    set egal "="

    set cTPN_FirableTransList [list]
    set cTPN_EnabledTransList [list]
    set listeMarking [list]
    set listeIndicePlace [list]
    
    set File [open $fichier r] 
    gets $File line

#    set markingAff ""
    set labelPlaceAff ""

    if {[string compare [nextExpression $line " "] "\[info\]"]==0} {
	gets $File line
    }

# On cree un marquage avec que des zero
    marquageNul
#    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
#	if {$tabPlace($tpn(courant),$i,statut)==$ok} {
#	    set tabPlace($tpn(courant),$i,jeton) 0
#	}
    #  }
    
    set theline [retirerStructure $line]
    set theline [split $theline " ="]

    set index0 [lsearch $theline 0]
    while {$index0>-1} {
	set index0 [lsearch $theline 0]
	set theline [lreplace $theline [expr $index0-1] $index0]

    }

    set leResultat ""
    set i 0
    while {$i< [llength $theline] -1} {
	set laVariable [lindex $theline $i]
	incr i
	set nbToken [lindex $theline $i]
	incr i

# wwwwwwwWwwwwwwwwwwwwwwwwwwWwwwwwwwwwwwwwwwwwwWwwwwwwwwwwwwwwwwwwWwwwwwwwwwwwwwwwwwwWwwwwwwwwwwwwwwwwwwWwwwwwwwwwwwwwwwwwwWwwwwwwwwwwwwwwwwwwWwwwwwwwwwwwwwwwwwwWwwwwwwwwwww

	set leBonTPN -1
	set indicePlace -1

	set nomSlave [sansEspace [nextExpression $laVariable "::"]]
	set idPlace [supNextExpression $laVariable "::"]

	
	if {[nulMarking $nbToken]==0} {
	
	    if {($nomSlave=="")||($idPlace=="")} {
		set leTPN [calculTPNCourant 0]
		if {[existIdP $leTPN $laVariable]} {
		    set leBonTPN $leTPN
		    set indicePlace [indiceIdP $leTPN $laVariable]
		    set leResultat "$leResultat $laVariable$egal$nbToken"
		}
	    } else {
		set idSlave [retrouverMasterSlaveFromNom $nomSlave]
		set leTPN [calculTPNCourant $idSlave]
		if {[existIdP $leTPN $idPlace]} {
		    set leBonTPN $leTPN
		    set indicePlace [indiceIdP $leTPN $idPlace]
		    set leResultat "$leResultat $nomSlave$doublepoint$idPlace$egal$nbToken"
		}
	    }
	set tabPlace($leBonTPN,$indicePlace,jeton) $nbToken
	}


#	    set positionIfAny [lsearch -exact $correspondanceIndiceIdentifiant(identifiant) $laVariable] 
#	    if {$positionIfAny>-1} {
#		set idPlaceIfAny [lindex $correspondanceIndiceIdentifiant(indice) $positionIfAny]
#		set tabPlace($tpn(courant),$idPlaceIfAny,jeton) $nbToken
#	    }
	    set  labelPlaceAff "$labelPlaceAff $laVariable=$nbToken"
    }

    set labelPlaceAff $leResultat
# On calcul le nouveau marquage
#    while {![finLigne $line]} {
#	set expMarking [nextExpression $line " "]
#	set nbToken [supNextExpression $expMarking "="]
#	set laVariable [sansEspace [nextExpression $expMarking "="]]
#	if {[string match *P* $expMarking]} 
#	if {$nbToken>0} {
#	    set positionIfAny [lsearch -exact $correspondanceIndiceIdentifiant(identifiant) $laVariable] 
#	    if {$positionIfAny>-1} {
#		set idPlaceIfAny [lindex $correspondanceIndiceIdentifiant(indice) $positionIfAny]
#		set tabPlace($tpn(courant),$idPlaceIfAny,jeton) $nbToken
#	    }
#	    set  labelPlaceAff "$labelPlaceAff $laVariable=$nbToken"
#	}
#	set line [supNextExpression $line " "]
#    }


#    afficheSimu "$markingAff \n$labelPlaceAff\n\n"

    if {$afficheState==1} {
	afficheSimu "$line \n\n"
    } else {
	afficheSimu "$labelPlaceAff\n (Other variables are hidden or are equal to zero) \n\n"
    }

    while {![eof $File]} {
      gets $File line


      if {[string compare [nextExpression $line " "] "\[info\]"]==0} {
	  set line [supNextExpression $line " "]
	  if {[string compare  [nextExpression $line " "] "Enabled:"]==0} {
	      set line [supNextExpression $line " "]
#	      set enabledTrans [withTransitionLabel $line [list ","]]
	      afficheSimu "Enabled transitions : "
	      afficheSimuColor "$line\n" brown
	      set cTPN_EnabledTransList [extractListeIndiceTransition $line -1]
	  } elseif {[string compare  [nextExpression $line " "] "Firable:"]==0} {
	      set line [supNextExpression $line " "]
#	      set fireableTrans [withTransitionLabel $line [list ","]]
	      afficheSimu "Firable transitions : "
	      afficheSimuColor "$line" green
	      set cTPN_FirableTransList [extractListeIndiceTransition $line -1]
	      if {$nbTokenColor($tpn(courant)) >0} {
		  set cTPN_FirableColoredTwiceTransList [extractListeIndiceTransition $line -2]
		  for {set uneCouleur 0} {$uneCouleur < $nbTokenColor($tpn(courant))} {incr uneCouleur} {
		      set cTPN_FirableTransListPerColor($uneCouleur) [extractListeIndiceTransition $line $uneCouleur]
		  }
	      }
	  }
      } else { 
	  afficheSimuColor "$line \n" blue
      }
    }



#puts $listeMarking
#puts $cTPN_FirableTransList
#puts $cTPN_EnabledTransList


    close $File
}

#proc enabledwithTransitionLabel {chaine listeSeparateur} {
#    set resul ""
#    while {[finLigne $chaine]==0} {
#	set resul "$resul [nextExpression $chaine "'t"]"
#	set chaine [supBeforeListSep [supNextExpression $chaine "'t"] $listeSeparateur]
#    }
#    return $resul
#}

proc  initialiserCorrespIdIdentifier {letpn} {
    global tabPlace tabTransition 
    global fin ok
    global correspondanceIndiceIdentifiant

  set correspondanceIndiceIdentifiant(indice) [list]
  set correspondanceIndiceIdentifiant(identifiant) [list]
 
    for {set i 1} {$tabPlace($letpn,$i,statut)!=$fin} {incr i} {
	if {$tabPlace($letpn,$i,statut)==$ok} {
	    lappend correspondanceIndiceIdentifiant(indice) $i
	    lappend correspondanceIndiceIdentifiant(identifiant) $tabPlace($letpn,$i,id)
	    }
    }

}


proc extractListeIndiceTransition {chaine couleur} {
    global tpn projet
    global sepColor 

    set resul [list]
    set underscore "_"

    while {[finLigne $chaine]==0} {
	set transition  [sansEspace [nextExpression $chaine ","]]
	set chaine [supNextExpression $chaine ","]
	set nomSlave [sansEspace [nextExpression $transition "::"]]
	set idTransSlave [sansEspace [supNextExpression $transition "::"]]

	if {$idTransSlave!=""} {
	    set transition $idTransSlave
	}
	set idTrans [nextExpression $transition $sepColor]
	set laColor [supNextExpression $transition $sepColor]

# on fait la liste pour toutes les transition ou seulement pour celles qui sont de couleur couleur
	if {($couleur < 0)||($couleur==$laColor)} {
	    if {$nomSlave==""} {
		set leTPN [calculTPNCourant 0]
		if {[existIdT $leTPN $idTrans]} {
		    
		    lappend resul "0_[indiceIdT $leTPN $idTrans]"
		}
	    } else {
		set idSlave [retrouverMasterSlaveFromNom $nomSlave]
		set leTPN [calculTPNCourant $idSlave]
		if {[existIdT $leTPN $idTrans]} {
		    lappend resul "$idSlave$underscore[indiceIdT $leTPN $idTrans]"
		}
	    }
	}
    }

    if {$couleur==-2} {
	set resul2 [list]
	while {[llength $resul]>0} {
	    set laTr [lindex $resul 0]
	    set resul [lrange $resul 1 end]
	    if {[lsearch $resul $laTr] >= 0} {
		lappend resul2 $laTr
		set resul [lremove $resul [lsearch $resul $laTr]]
	    }
	}
	set resul $resul2
    }
    
		
    return $resul
}

#--------------- INIT RESET QUIT.... simulator

#---------------- Initialisation de la simulation 

proc initSimulation {} {
    global nomRdP tpn
    global cheminTemp simulOption
    global romeoPath
    global nomSimul
    # variables globales pour le calcul
    global cTPN_CurrentDomain cTPN_CurrentMarking
    global cTPN_FirableTransList cTPN_EnabledTransList cTPN_FirableColoredTwiceTransList  cTPN_FirableTransListPerColor
   global firingSequence firingSequenceTotal
    global methode parameters typePN computOption
  global correspondanceIndiceIdentifiant InitialToken

    #typePN : -1 : stopwatch ;   -2 scheduling ; -3 hybrid ; 1 t-tpn ; 2 p-tpn
#parameters: 1 real 2 integer

	if {$typePN==-2} {
	    set simulOption(1) "-s"
	} elseif  {$typePN==-3} {
	    set simulOption(1) "-w"
	} elseif  {$typePN==-1} {
	    set simulOption(1) "-w"
	} else {
	    set simulOption(1) "-t"
	}

	# Initialiser le calcul parametres entiers ou non

# rappel computOption(hull) = 1 si enveloppe sur projection sur param OU 2 si enveloppe sur tout
#	if {$parameters==2} {
#	    set simulOption(2) "-pia"
#	} elseif {$parameters==1} {
#	    set simulOption(2) "-pp"
#	} elseif {$methode==1} {
#	    set simulOption(2) "-z"
#	} else {
#	    set simulOption(2) "-g"
#	}
    set firingSequence [list]
    set firingSequenceTotal [list]
    set listeVide [list]

    fireSequenceTransition $listeVide
}

proc quitterSimulate {} {
    global tabPlace InitialToken marquageCourant ok fin projet
    global tpn tabUnDo
    global simulator typePN 

#    if {($simulator(gpn))&&($scheduling)} {
#	set retour [gpns_finalPolka]
#    }
    destroy .fenetreSimul

    remettreMarquage 1
}

proc remettreMarquage {initial} {
    global tabPlace  ok fin projet
    global tpn tabUnDo
    global simulator typePN
    global InitialToken marquageCourant

    if {$initial} {
	set leMaster [calculTPNCourant 0]
	for {set i 1} {$tabPlace($leMaster,$i,statut)!=$fin} {incr i} {
	    if {$tabPlace($leMaster,$i,statut)==$ok} {
		set tabPlace($leMaster,$i,jeton) $InitialToken(0,$i)
	    }
	}

	for {set indiceSlave 1} {$indiceSlave<=$projet($tpn(onglet),nbInput)}  {incr indiceSlave} {
	    if {$projet($tpn(onglet),input,$indiceSlave,status) != "deleted"} {

		set leSlave [calculTPNCourant $indiceSlave]

		for {set i 1} {$tabPlace($leSlave,$i,statut)!=$fin} {incr i} {
		    if {$tabPlace($leSlave,$i,statut)==$ok} {
			set tabPlace($leSlave,$i,jeton) $InitialToken($indiceSlave,$i)
		    }
		}
	    }
	}
    } else {
	set leMaster [calculTPNCourant 0]
	for {set i 1} {$tabPlace($leMaster,$i,statut)!=$fin} {incr i} {
	    if {$tabPlace($leMaster,$i,statut)==$ok} {
		set tabPlace($leMaster,$i,jeton) $marquageCourant(0,$i)
	    }
	}


	for {set indiceSlave 1} {$indiceSlave<=$projet($tpn(onglet),nbInput)}  {incr indiceSlave} {
	    if {$projet($tpn(onglet),input,$indiceSlave,status) != "deleted"} {

		set leSlave [calculTPNCourant $indiceSlave]

		for {set i 1} {$tabPlace($leSlave,$i,statut)!=$fin} {incr i} {
		    if {$tabPlace($leSlave,$i,statut)==$ok} {
			set tabPlace($leSlave,$i,jeton) $marquageCourant($indiceSlave,$i)
		    }
		}
	    }
	}
    }
}



proc marquageNul {} {
    global tabPlace  ok fin projet
    global tpn tabUnDo
    global simulator typePN

    set leMaster [calculTPNCourant 0]
    for {set i 1} {$tabPlace($leMaster,$i,statut)!=$fin} {incr i} {
	if {$tabPlace($leMaster,$i,statut)==$ok} {
	    set tabPlace($leMaster,$i,jeton) 0
	}
    }


    for {set indiceSlave 1} {$indiceSlave<=$projet($tpn(onglet),nbInput)}  {incr indiceSlave} {
	    if {$projet($tpn(onglet),input,$indiceSlave,status) != "deleted"} {

		set leSlave [calculTPNCourant $indiceSlave]

		for {set i 1} {$tabPlace($leSlave,$i,statut)!=$fin} {incr i} {
		    if {$tabPlace($leSlave,$i,statut)==$ok} {
			set tabPlace($leSlave,$i,jeton) 0
		    }
		}
	    }
    }
}

proc enregistrerMarquageInitial {} {
    global tabPlace ok fin projet
    global tpn tabUnDo
    global simulator typePN InitialToken

    set leMaster [calculTPNCourant 0]
    for {set i 1} {$tabPlace($leMaster,$i,statut)!=$fin} {incr i} {
	if {$tabPlace($leMaster,$i,statut)==$ok} {
	    set InitialToken(0,$i) $tabPlace($leMaster,$i,jeton) 
	}
    }


    for {set indiceSlave 1} {$indiceSlave<=$projet($tpn(onglet),nbInput)}  {incr indiceSlave} {
	    if {$projet($tpn(onglet),input,$indiceSlave,status) != "deleted"} {

		set leSlave [calculTPNCourant $indiceSlave]
		for {set i 1} {$tabPlace($leSlave,$i,statut)!=$fin} {incr i} {
		    if {$tabPlace($leSlave,$i,statut)==$ok} {
			set InitialToken($indiceSlave,$i) $tabPlace($leSlave,$i,jeton) 
		    }
		}
	    }
    }
}

proc enregistrerMarquageCourant {} {
    global tabPlace ok fin projet
    global tpn tabUnDo
    global simulator typePN marquageCourant

    set leMaster [calculTPNCourant 0]
    for {set i 1} {$tabPlace($leMaster,$i,statut)!=$fin} {incr i} {
	if {$tabPlace($leMaster,$i,statut)==$ok} {
	    set marquageCourant(0,$i) $tabPlace($leMaster,$i,jeton) 
	}
    }


    for {set indiceSlave 1} {$indiceSlave<=$projet($tpn(onglet),nbInput)}  {incr indiceSlave} {
	    if {$projet($tpn(onglet),input,$indiceSlave,status) != "deleted"} {
#		set prefixe "[sansXml $projet($tpn(onglet),input,$i,file)]::"
		set leSlave [calculTPNCourant $indiceSlave]
		for {set i 1} {$tabPlace($leSlave,$i,statut)!=$fin} {incr i} {
		    if {$tabPlace($leSlave,$i,statut)==$ok} {
			set marquageCourant($indiceSlave,$i) $tabPlace($leSlave,$i,jeton) 
		    }
		}
	    }
    }
}


proc resetSimul {c} {
    global tabPlace InitialToken ok fin 
    global tpn tabUnDo
    global methode parameters typePN
    global cTPN_CurrentDomain cTPN_CurrentMarking
    global cTPN_FirableTransList cTPN_EnabledTransList cTPN_FirableColoredTwiceTransList  cTPN_FirableTransListPerColor
    global firingSequence firingSequenceTotal
    global nomSimul


    if {$methode==1} {set zoneClass "Zone"} else {set zoneClass "Class"}
    afficheSimu "\n"
    afficheSimuColor "Restarting simulation with initial marking and initial $zoneClass\n" fondgris
#    afficheSimuColor "Sequence from initial marking : \n" brown
    afficheSimu "-----------------------\n"
    afficheSimu "$zoneClass\:\n"
    remettreMarquage 1

    initSimulation
	#afficheSimu [printDomain $cSState]
    MAJdessinsProjetcourant .romeo.global

}



proc extractEnabled {i} {
    global cTPN_EnabledTransList
    
#	return [contains $cTPN_EnabledTransList $i]
   set indice [lsearch  $cTPN_EnabledTransList $i]
    if {$indice > -1} {
	return 1
    } else {
	return 0
    }
#return  [lsearch  $cTPN_EnabledTransList $i]
}


proc enabled {i} {
    global cTPN_EnabledTransList
    
#	return [contains $cTPN_EnabledTransList $i]
   set indice [lsearch  $cTPN_EnabledTransList $i]
    if {$indice > -1} {
	return 1
    } else {
	return 0
    }
#return  [lsearch  $cTPN_EnabledTransList $i]
}

proc nulMarking {marking} {
    
    if {[retirerListeCar $marking  [list , 0 " "]] ==""} {
	return 1
    } else {
	return 0
    }
}



proc verifierPoidsCouleur {marking} {
    
    if {[retirerListeCar $marking  [list , 0 " "]] ==""} {
	return 1
    } else {
	return 0
    }
}



proc firableTwice {i} {
    global cTPN_FirableTransList cTPN_EnabledTransList cTPN_FirableColoredTwiceTransList  cTPN_FirableTransListPerColor

    
    set indice  [lsearch  $cTPN_FirableColoredTwiceTransList $i]
    if {$indice > -1} {
	return 1
    } else {
	return 0
    }

}

proc coloredFirableOnce {i} {
    global cTPN_FirableTransList cTPN_EnabledTransList cTPN_FirableColoredTwiceTransList  cTPN_FirableTransListPerColor
    global nbTokenColor
    global tpn
    set resCouleur -1
    
    for {set uneCouleur 0} {$uneCouleur < $nbTokenColor($tpn(courant))} {incr uneCouleur} {
	if {[lsearch  $cTPN_FirableTransListPerColor($uneCouleur) $i]>=0} {
	    set resCouleur $uneCouleur
	}
    }
    return $resCouleur

}

proc firable {i} {
    global cTPN_FirableTransList
    
set indice  [lsearch  $cTPN_FirableTransList $i]

   if {$indice > -1} {
	return 1
    } else {
	return 0
    }

 }

proc boutonSimTPN {w c} {
    global simulatorOn

    destroy $w.barreHaut.simulate
    destroy $w.barreHaut.edit 
    button $w.barreHaut.simulate -text "Simulator"  -font menufont -command "simulateTPN $w $c" -state disabled
    pack configure $w.barreHaut.simulate -side right -padx 5  

    button $w.barreHaut.edit -text "Editor" -font menufont -command "editTPN $w $c" -state normal
    pack configure $w.barreHaut.edit -side right -padx 5 
}

proc quitterSimulBrutalement {} {
    editTPN .romeo.global .romeo.global.frame.c
}

proc editTPN {w c} {
    global simulatorOn
    global tabPlace InitialToken ok fin tpn
    affiche "\n"
    affiche [mc "-Stopping simulator..."]
    quitterSimulate
    set simulatorOn 0
    destroy $w.barreHaut.simulate
    destroy $w.barreHaut.edit 
    button $w.barreHaut.simulate -text "Simulator" -font menufont -command "simulateTPN $w $c" -state normal
    pack configure $w.barreHaut.simulate -side right -padx 5  

    button $w.barreHaut.edit -text "Editor" -font menufont -command "editTPN $w $c" -state disabled
    pack configure $w.barreHaut.edit -side right -padx 5 
    MAJdessinsProjetcourant $w
    affiche "ok" 
}

proc retirerStructure {lastring} {


    while {[string first "\{" $lastring] >=0} {
	
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

	set avantStruct [string range $lastring 0  [expr $debutStruct -1 ] ]
	set apresStruct [string range $lastring [expr $finStruct+1] [string length $lastring]]
	set remplaceStruct "0"
	set lastring $avantStruct$remplaceStruct$apresStruct
    }

    while {[string first "\[" $lastring] >=0} {
	
	set parens  [regexp -inline -all {[\[\]]} $lastring]
	set balance 0
	set nbFermeture 0
	set change("\[")  1   ;# This technique saves an if-block :)
	set change("\]") -1

	set fin 0
	# fermeture recupere le nombre de fermetures d'acolade avant equilibre (ouverture = fermeture)
	foreach p $parens {
	    incr balance $change(\"$p\")
	    if {($balance==0)} {
		set fin 1
	    } else {
		if {($p=="\[")&&($fin==0)} {
		    incr nbFermeture
		}
	    }
	}

	set debutStruct [occurence $lastring 1 "\["]
	set finStruct [occurence $lastring $nbFermeture "\]"]

	set avantStruct [string range $lastring 0  [expr $debutStruct -1 ] ]
	set apresStruct [string range $lastring [expr $finStruct+1] [string length $lastring]]

	set remplaceStruct [sansEspace [string range $lastring [expr $debutStruct +1 ] [expr $finStruct-1]]]
	
	set lastring $avantStruct$remplaceStruct$apresStruct
    }

    return $lastring

}
