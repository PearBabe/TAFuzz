# This file is part of the Roméo model-checking software
# 
# Copyright University of Nantes, École Centrale de Nantes, IRCCyN
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

#procedures  Control Panel et associ�es
#*
#*********


proc controlPanel {w c} {
    global nomRdP
    global francais
    global infini
    global parameters allowedArc outFormat computOption typePN hideGU cost controle couleurPN
    global simulatorOn
    global tabPlace tabJeton ok fin 
    global tpn tabUnDo
    global ancienAllowedArc ancienMode
    global firstTime
    global nb
    global nbProcesseur
    global modif 
    global avecDeveloppementEncours boutonIdentifier


# met a disable le bouton control panel de la barre du haut    
#    destroy $w.barreHaut.d.control
#    button $w.barreHaut.d.control -text [mc "Control Panel"] -command "controlPanel $w $c"  -state disabled
#    pack $w.barreHaut.d.control -side right -padx 5
    
    # ++++++++++++++++ Creation de la fenetre d'affichage ++++++++++++++++++

    catch {destroy .control}
    toplevel .control
    wm title .control [mc "Control panel"]
    wm protocol .control WM_DELETE_WINDOW {disableControl .romeo.global .romeo.global.frame.c}

#	set x [expr [winfo x .romeo]+[winfo width .romeo]]
	set y [expr [winfo y .romeo]]
#	wm geometry .control +$x+$y

	wm geometry .control +0+$y
if {$firstTime(control)} {
	wm geometry .romeo +155+$y
	set firstTime(control) 0
}

#pour ne pas avoir les 3 boutons en haut
#	wm overrideredirect .control on

    frame .control.frame -width 135
    set s .control.frame 
    pack $s -side right -pady 2m -padx 10
#    frame $s.marge
#    pack $s.marge -side top -pady 20
#    label $s.titre -text [mc "Control Panel"]
#    pack $s.titre -side top -pady 4
    
    # type de TPN
#    set ancienMode(scheduling) $scheduling 
    set ancienMode(couleurPN) $couleurPN
    set ancienMode(cost) $cost
    set ancienMode(controle) $controle
    set ancienMode(parameters) $parameters
    set ancienMode(typePN) $typePN
#    set ancienMode(hull) $computOption(hull)


    frame $s.optionTPN -relief solid -bd 1
    label $s.optionTPN.label
    pack $s.optionTPN.label -side top -pady 2 -anchor w
    $s.optionTPN.label config -text [mc "Petri net type:"] -font menufont 
    pack $s.optionTPN -side top -fill x
    radiobutton $s.optionTPN.pn -text "Untimed (PN)" -font menufont  -variable typePN -value 0 -selectcolor red -command "validControl $w $c"
    radiobutton $s.optionTPN.ttpn -text "Time (T-TPN)" -font menufont -variable typePN -value 1 -selectcolor red -command "validControl $w $c"

    set OlivierBoutin 0
    if {$OlivierBoutin}  {
	# deb P-TPN ---------------
	radiobutton $s.optionTPN.ptpn -text "Time (P-TPN)" -font menufont -variable typePN -value 2 -selectcolor red -command "validControl $w $c"
	# fin P-TPN ---------------
    } else {
	if {$typePN==2} {set typePN 1}
    }

	radiobutton $s.optionTPN.stopwatch -text "Stopwatch-T-TPN -> timed inhibitor arcs" -font menufont -variable typePN -value -1  -selectcolor red -command "validControl $w $c"
#    radiobutton $s.optionTPN.schedule -text [mc "Scheduling-T-TPN"] -variable typePN -value -2  -selectcolor red -command "validControl $w $c"
    radiobutton $s.optionTPN.hybrid -text [mc "Hybrid-T-TPN"] -font menufont  -variable typePN -value -3  -selectcolor red -command "validControl $w $c"

    pack $s.optionTPN.pn -side top -pady 2 -anchor w
    pack $s.optionTPN.ttpn -side top -pady 2 -anchor w

    if {$OlivierBoutin}  {
	# deb P-TPN ---------------
	pack $s.optionTPN.ptpn -side top -pady 2 -anchor w
	# fin P-TPN ---------------
    }

    pack $s.optionTPN.stopwatch -side top -pady 2 -anchor w
#    pack $s.optionTPN.schedule -side top -pady 2 -anchor w
    pack $s.optionTPN.hybrid -side top -pady 2 -anchor w

 # Definition et choix du scheduler

#    frame $s.fenetreScheduler -relief solid -bd 1
#    pack $s.fenetreScheduler -side top -pady 2 -anchor w -fill x  

 #   if {$typePN ==-2} {
 #     button $s.optionTPN.define -state active -text [mc "Define scheduler..."]  -command "definirProcesseur $c"
 #   } else {
 #     button $s.optionTPN.define -state disabled -text [mc "Define scheduler..."]  -command "definirProcesseur $c"
 #   }
 #   pack $s.optionTPN.define  -side left -expand 1

# parameters
    frame $s.parametre -relief solid -bd 1
    pack $s.parametre -side top -pady 2 -anchor w -fill x
    label $s.parametre.label
    pack $s.parametre.label -side top -pady 2 -anchor w
    $s.parametre.label config -text [mc "Parameters:"] -font menufont 

    radiobutton $s.parametre.paramNo -text "No" -font menufont -variable parameters -value 0 -selectcolor red -command "validParametre $w $c"
    radiobutton $s.parametre.paramYes -text "Real parameters" -font menufont -variable parameters -value 1 -selectcolor red -command "validParametre $w $c"
    radiobutton $s.parametre.paramUnder -text "Integer-preserving underapproximation" -font menufont  -variable parameters -value 3 -selectcolor red -command "validParametre $w $c"
    radiobutton $s.parametre.paramInt -text "Integer parameters" -font menufont -variable parameters -value 2 -selectcolor red -command "validParametre $w $c"

#    radiobutton $s.parametre.paramIntNew -text "Integer Parametric DBM (New)" -variable parameters -value 3 -selectcolor red -command "validParametre $w $c"

pack $s.parametre.paramNo -side top -pady 2 -anchor w
    pack $s.parametre.paramYes -side top -pady 2 -anchor w
    pack $s.parametre.paramUnder -side top -pady 2 -anchor w
    pack $s.parametre.paramInt -side top -pady 2 -anchor w
#    pack $s.parametre.paramIntNew -side top -pady 2 -anchor w

# parameters Integer Hull
#    frame $s.parametre.integer
#    pack $s.parametre.integer -side top -pady 2 -anchor w -fill x
#    label $s.parametre.integer.marge
#    $s.parametre.integer.marge config -text "      "
#    pack $s.parametre.integer.marge -side left -pady 2 -anchor w
#    frame $s.parametre.integer.hull 
#    pack $s.parametre.integer.hull -side top -pady 2 -anchor w -fill x
#    radiobutton $s.parametre.integer.hull.full -text "full integer hull" -variable computOption(hull) -value 2 -selectcolor red -command "validParametre $w $c"
#    radiobutton $s.parametre.integer.hull.nofull -text "integer hull only on parameters" -variable computOption(hull) -value 1 -selectcolor red -command "validParametre $w $c"

#    pack $s.parametre.integer.hull.full -side top -pady 2 -anchor w
#    pack $s.parametre.integer.hull.nofull -side top -pady 2 -anchor w

#    if {$parameters < 2} { 
#    	$s.parametre.integer.hull.nofull configure -state disabled
#    	$s.parametre.integer.hull.full configure -state disabled
#    }


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# cost
    frame $s.cost -relief solid -bd 1
    pack $s.cost -side top -pady 2 -anchor w -fill x
    label $s.cost.label
    pack $s.cost.label -side top -pady 2 -anchor w
    $s.cost.label config -text [mc "Cost PN:"] -font menufont 

    radiobutton $s.cost.costNo -text "No" -font menufont -variable cost -value 0 -selectcolor red -command "validCost $w $c"
    radiobutton $s.cost.costYesHybrid -text "Cost (Polyhedron)" -font menufont -variable cost -value 1 -selectcolor red -command "validCost $w $c"
#    radiobutton $s.cost.costYesOptim -text "Cost (DBM + Polyhedron)" -variable cost -value 3 -selectcolor red -command "validCost $w $c"
    radiobutton $s.cost.costYesSplit -text "Cost (Split)" -font menufont -variable cost -value 2 -selectcolor red -command "validCost $w $c"
#    radiobutton $s.cost.costYesGlobal -text "Cost (global time DBM approach)" -variable cost -value 4 -selectcolor red -command "validCost $w $c"

    pack $s.cost.costNo -side top -pady 2 -anchor w
#    pack $s.cost.costYesGlobal -side top -pady 2 -anchor w
    pack $s.cost.costYesHybrid -side top -pady 2 -anchor w
#    pack $s.cost.costYesOptim -side top -pady 2 -anchor w
    pack $s.cost.costYesSplit -side top -pady 2 -anchor w

    if {($typePN<-1)||($typePN>1)} {
	if {$cost>0} {set cost 0 }
	$s.cost.costNo configure -state active
#	$s.cost.costYesGlobal  configure -state disabled
	$s.cost.costYesHybrid  configure -state disabled
#	$s.cost.costYesOptim  configure -state disabled
	$s.cost.costYesSplit  configure -state disabled
    }

    if {$typePN==-1} {
	if {$cost>1} {set cost 1 }
	$s.cost.costNo configure -state active
#	$s.cost.costYesGlobal  configure -state disabled
	$s.cost.costYesHybrid  configure -state active
#	$s.cost.costYesOptim  configure -state disabled
	$s.cost.costYesSplit  configure -state disabled
    }



# typePN : -1 : stopwatch ;   -2 scheduling ; 1 t-tpn ; 2 p-tpn ; -3 hybrid
    if {$typePN<=-1} {
	if {$parameters>1} {set parameters 1 }
	$s.parametre.paramNo configure -state active
    	$s.parametre.paramYes configure -state active
        $s.parametre.paramInt configure -state disabled
	$s.parametre.paramUnder  configure -state disabled
    }

    if {($typePN == 2)} { 
	$s.parametre.paramNo configure -state disabled
    	$s.parametre.paramYes configure -state disabled
        $s.parametre.paramInt configure -state disabled
	$s.parametre.paramUnder  configure -state disabled

#    	$s.parametre.integer.hull.nofull configure -state disabled
#    	$s.parametre.integer.hull.full configure -state disabled
    }



# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# controle

    frame $s.controle -relief solid -bd 1
    pack $s.controle -side top -pady 2 -anchor w -fill x
    label $s.controle.label
    pack $s.controle.label -side top -pady 2 -anchor w
    $s.controle.label config -text [mc "Control PN:"] -font menufont 


    radiobutton $s.controle.controlNo -text "No" -font menufont -variable controle -value 0 -selectcolor red -command "validControlPN $w $c"

    radiobutton $s.controle.untimed -text "Untimed control PN" -font menufont  -variable controle -value 1 -selectcolor red -command "validControlPN $w $c"
    radiobutton $s.controle.timed -text "Timed control PN (zone)" -font menufont  -variable controle -value 2 -selectcolor red -command "validControlPN $w $c"
    radiobutton $s.controle.timedClass -text "Timed control PN (class)" -font menufont   -variable controle -value 3 -selectcolor red -command "validControlPN $w $c"

    pack $s.controle.controlNo -side top -pady 2 -anchor w
    pack $s.controle.untimed -side top -pady 2 -anchor w
    pack $s.controle.timed -side top -pady 2 -anchor w
    pack $s.controle.timedClass -side top -pady 2 -anchor w

     if { $controle>=1} {
	  set cost 0
	 if {$typePN==-2} { set typePN 1}

	 if { $controle==1} {
#	     .control.frame.optionTPN.define configure -state disabled
	     .control.frame.parametre.paramNo configure -state disabled
	     .control.frame.parametre.paramYes configure -state disabled
	     .control.frame.parametre.paramInt configure -state disabled
	     .control.frame.parametre.paramUnder configure -state disabled

	     .control.frame.optionTPN.ttpn configure -state disabled
	     .control.frame.optionTPN.stopwatch configure -state disabled
#	     .control.frame.optionTPN.schedule configure -state disabled
	     .control.frame.optionTPN.hybrid configure -state disabled
	 }
#          .control.frame.optionTPN.define configure -state disabled
#          .control.frame.optionTPN.schedule configure -state disabled
	  .control.frame.cost.costNo  configure -state disabled
	  .control.frame.cost.costYesHybrid  configure -state disabled
	  .control.frame.cost.costYesSplit  configure -state disabled
#	  $w.barreHaut.simulate configure -state disabled
     } 

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

 #    if { $couleurPN>=1} {
#	  set cost 0
#	 if {$typePN==-2} { set typePN 1}
#
#	 if { $controle==1} {
#	     .control.frame.optionTPN.define configure -state disabled
#	     .control.frame.parametre.paramNo configure -state disabled
#	     .control.frame.parametre.paramYes configure -state disabled
#	     .control.frame.parametre.paramInt configure -state disabled
#	     .control.frame.parametre.paramUnder configure -state disabled
#
#	     .control.frame.optionTPN.ttpn configure -state disabled
#	     .control.frame.optionTPN.stopwatch configure -state disabled
#	     .control.frame.optionTPN.schedule configure -state disabled
#	     .control.frame.optionTPN.hybrid configure -state disabled
#	 }
 #         .control.frame.optionTPN.define configure -state disabled
  #        .control.frame.optionTPN.schedule configure -state disabled
#	  .control.frame.cost.costNo  configure -state disabled
#	  .control.frame.cost.costYesHybrid  configure -state disabled
#	  .control.frame.cost.costYesSplit  configure -state disabled
#	  $w.barreHaut.simulate configure -state disabled
#     } 

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # type d'arc  ----------COMMENTAIRE CAR CA NE SERT A RIEN
    
#    frame $s.arc -relief solid -bd 1
#    pack $s.arc -side top -pady 2 -anchor w -fill x
#    label $s.arc.label
#    pack $s.arc.label -side top -pady 2 -anchor w
#    $s.arc.label config -text [mc "Logical arcs:"]
    set ancienAllowedArc(reset) $allowedArc(reset)
    set ancienAllowedArc(read) $allowedArc(read)
    set ancienAllowedArc(logicInhibitor) $allowedArc(logicInhibitor)

#    checkbutton $s.arc.reset -text [mc "Reset arcs"]  -variable allowedArc(reset) \
#	-relief flat -anchor w -selectcolor red -command "validArc $w $c"
#    pack $s.arc.reset -side top -pady 2 -anchor w
    
#    checkbutton $s.arc.read -text [mc "Read arcs"]  -variable allowedArc(read) \
#	-relief flat -anchor w -selectcolor red -command "validArc $w $c"
#    pack $s.arc.read -side top -pady 2 -anchor w

#    checkbutton $s.arc.logicInh -text [mc "Logical inhibitor arcs"]  -variable allowedArc(logicInhibitor)  \
#	-relief flat -anchor w -selectcolor red -command "validArc $w $c"
#    pack $s.arc.logicInh -side top -pady 2 -anchor w


  frame $s.affichage -relief solid -bd 1
    pack $s.affichage -side top -pady 2 -anchor w -fill x
    label $s.affichage.label
    pack $s.affichage.label -side top -pady 2 -anchor w
    $s.affichage.label config -text "Hide Guards, Updates, label and identifier" -font menufont 
    set ancienHideGU(guard) $hideGU(guard) 
    set ancienHideGU(update) $hideGU(update) 
    set ancienHideGU(Plabel) $hideGU(Plabel) 
    set ancienHideGU(Pidentifier) $hideGU(Pidentifier) 
    set ancienHideGU(Tlabel) $hideGU(Tlabel) 
    set ancienHideGU(Tidentifier) $hideGU(Tidentifier) 

    frame $s.affichage.gu
    pack $s.affichage.gu -side top -pady 2 -anchor w -fill x

checkbutton $s.affichage.gu.garde -text guard -font menufont  -variable hideGU(guard) \
	-relief flat -anchor w -selectcolor red -command "validaffichage $w"
    pack  $s.affichage.gu.garde -side left -pady 2 -anchor w
    
    checkbutton $s.affichage.gu.update -text update -font menufont  -variable hideGU(update) \
	-relief flat -anchor w -selectcolor red -command "validaffichage $w"
    pack $s.affichage.gu.update -side right -pady 2 -anchor w
 
    frame $s.affichage.place
    pack $s.affichage.place -side top -pady 2 -anchor w -fill x

    checkbutton $s.affichage.place.plabel -text "Place label" -font menufont  -variable hideGU(Plabel) \
	-relief flat -anchor w -selectcolor red -command "validaffichage $w"
    pack  $s.affichage.place.plabel -side left -pady 2 -anchor w

    checkbutton $s.affichage.place.pidentifier -text "Place identifier" -font menufont   -variable hideGU(Pidentifier) \
	-relief flat -anchor w -selectcolor red -command "validaffichage $w"
    pack  $s.affichage.place.pidentifier -side right -pady 2 -anchor w

    frame $s.affichage.transition
    pack $s.affichage.transition -side top  

    checkbutton $s.affichage.transition.tlabel -text "Transition label" -font menufont   -variable hideGU(Tlabel) \
	-relief flat -anchor w -selectcolor red -command "validaffichage $w"
    pack  $s.affichage.transition.tlabel -side left -pady 2 -anchor w

    checkbutton $s.affichage.transition.tidentifier -text "Transition identifier" -font menufont  -variable hideGU(Tidentifier) \
	-relief flat -anchor w -selectcolor red -command "validaffichage $w"
    pack  $s.affichage.transition.tidentifier -side right 

    checkbutton $s.affichage.boutonidentifier -text "P/T identifier <- P/T label" -font menufont  -variable boutonIdentifier \
	-relief flat -anchor w -selectcolor red 

   pack  $s.affichage.boutonidentifier -side top -pady 2 -anchor w

#------------------------------------------On supprime le 19 septembre 2014 ces options-------------------
#  # Option de fin de calcul
    
#    frame $s.stop -relief solid -bd 1
#    pack $s.stop -side top -pady 2 -anchor w -fill x
#    label $s.stop.label
#    pack $s.stop.label -side top -pady 2 -anchor w
#    $s.stop.label config -text [mc "Stop conditions (none if -1):"]
##    set ancienAllowedArc(reset) $allowedArc(reset)
    
#    frame $s.stop.node
#    pack $s.stop.node -side top -pady 2 -anchor w
#	entry $s.stop.node.saisie -justify left -textvariable computOption(node) -relief sunken -width 10 -bg white 
#	pack $s.stop.node.saisie -side left
#    label $s.stop.node.label -text [mc ": nodes (class or symbolic state)"]       	
#    pack $s.stop.node.label -side left
    
    
#    frame $s.stop.token
#    pack $s.stop.token -side top -pady 2 -anchor w
#	entry $s.stop.token.saisie -justify left -textvariable computOption(token) -relief sunken -width 10 -bg white
#	pack $s.stop.token.saisie -side left
#    label $s.stop.token.label -text [mc ": p-bound (max 50 000)"]       	
#    pack $s.stop.token.label -side left

# # unfolding stop condition   

    
#    frame $s.stop.event
#    pack $s.stop.event -side top -pady 2 -anchor w
#	entry $s.stop.event.saisie -justify left -textvariable computOption(event) -relief sunken -width 10 -bg white 
#	pack $s.stop.event.saisie -side left
#    label $s.stop.event.label -text ": maximum events (unfolding)"     	
#    pack $s.stop.event.label -side left
    
#    frame $s.stop.depth
#    pack $s.stop.depth -side top -pady 2 -anchor w
#	entry $s.stop.depth.saisie -justify left -textvariable computOption(depth) -relief sunken -width 10 -bg white
#	pack $s.stop.depth.saisie -side left
#    label $s.stop.depth.label -text ": maximum depth (unfolding)"       	
#    pack $s.stop.depth.label -side left
    
#---------------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------------
    # format des fichiers - espace d'etat et automate
    
#    frame $s.format -relief solid -bd 1
#    pack $s.format -side top -fill x
#    label $s.format.label -text [mc "Output file format:"]
#    pack $s.format.label -side top -pady 2 -anchor w
#    frame $s.format.scg -relief solid -bd 1 
#    pack $s.format.scg -side top -fill x -padx 3 -pady 2
#    label $s.format.scg.label -text [mc "State space:"]
#    pack $s.format.scg.label -side top -pady 2 -anchor w
#    radiobutton $s.format.scg.text -text "Text" -variable outFormat(scg) -value 1 -selectcolor red -command "save_preferences"
#    radiobutton $s.format.scg.mec -text "MEC" -variable outFormat(scg) -value 2  -selectcolor red -command "save_preferences"
#    radiobutton $s.format.scg.aldebaran -text "Aldebaran" -variable outFormat(scg) -value 3  -selectcolor red -command "save_preferences"


#    pack $s.format.scg.text -side top -pady 2 -anchor w
#    pack $s.format.scg.aldebaran -side top -pady 2 -anchor w
#    pack $s.format.scg.mec -side top -pady 2 -anchor w

    # format des fichiers - automate
    
#    frame $s.format.automate -relief solid -bd 1
#    label $s.format.automate.label
#    pack $s.format.automate -side top -fill x -padx 3
#    pack $s.format.automate.label -side top -pady 2 -anchor w
#    $s.format.automate.label config -text [mc "Timed Automata:"]
#    radiobutton $s.format.automate.uppaal -text "UPPAAL" -variable outFormat(ta) -value 1 -selectcolor red -command "save_preferences"
#    radiobutton $s.format.automate.kronos -text "Kronos" -variable outFormat(ta) -value 2  -selectcolor red -command "save_preferences"

#    pack $s.format.automate.uppaal -side top -pady 2 -anchor w
#    pack $s.format.automate.kronos -side top -pady 2 -anchor w
    
    button $s.disable -text [mc "Close"] \
	-command "disableControl $w $c"
    pack $s.disable -side top
}

proc disableControl {w c} {
    global simulatorOn computOption
    global tabPlace tabJeton ok fin
    global tpn tabUnDo

    destroy $w.barreHaut.d.control
    button $w.barreHaut.d.control -text [mc "Control Panel"] -command "controlPanel $w $c" -font menufont
    pack $w.barreHaut.d.control -side right -padx 5

   #OPTION MAXTOKEN
    if {[catch {set x [format %d $computOption(token)]} erreur]} { 
	set computOption(token) 50000
    } elseif {($x>50000)||($x<-1)} {
	set computOption(token) 50000 
    } 
    if {[catch {set x [format %d $computOption(node)]} erreur]} { 
	set computOption(node) -1
    } elseif {$x<-1} {
	set computOption(node) -1 
    } 
    if {[catch {set x [format %d $computOption(event)]} erreur]} { 
	set computOption(event) -1
    } elseif {$x<-1} {
	set computOption(event) -1 
    } 
    if {[catch {set x [format %d $computOption(depth)]} erreur]} { 
	set computOption(depth) -1
    } elseif {$x<-1} {
	set computOption(depth) -1 
    } 

    destroy .control
#    redessinerRdP $c
    MAJdessinsProjetcourant $w
}

proc validaffichage {w} {
global computOption
global hideGU

    save_preferences
    MAJdessinsProjetcourant $w

}


proc validArc {w c} {
    global scheduling parameters allowedArc outFormat typePN
    global simulatorOn computOption
    global ancienAllowedArc
    global modif 
    global tpn tabUnDo


    if {$simulatorOn==0} {
	destroy $w.barreGauche.p
	destroy $w.barreGauche.seph
	creerBarreDessin $w $c
	save_preferences
	MAJdessinsProjetcourant $w 
	set ancienAllowedArc(reset) $allowedArc(reset)
	set ancienAllowedArc(read) $allowedArc(read)
	set ancienAllowedArc(logicInhibitor) $allowedArc(logicInhibitor)
	queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0
    } else {
	set allowedArc(reset) $ancienAllowedArc(reset)
	set allowedArc(read) $ancienAllowedArc(read)
	set allowedArc(logicInhibitor) $ancienAllowedArc(logicInhibitor)
    }
}

proc validParametre {w c} {
    global scheduling allowedArc outFormat parameters typePN computOption
    global simulatorOn
    global ancienMode
    global modif
    global tpn tabUnDo


    if {$simulatorOn==0} {
	# remarque ($ancienMode(parameters)==0) || ($parameters ==0) signfie que l'un des deux modes n'est pas parametrique
	if {($ancienMode(parameters) != $parameters)} {
	    if {($ancienMode(parameters)==0) || ($parameters ==0)} {
		heriterContrainteTempo $parameters $tpn(courant)
	    }
        }
	validControl $w $c

    } else {
	set parameters $ancienMode(parameters)
#	set computOption(hull) $ancienMode(hull)
    }
}



proc validCost {w c} {
    global scheduling allowedArc outFormat parameters typePN computOption cost
    global simulatorOn
    global ancienMode
    global modif
    global tpn tabUnDo

    if {$simulatorOn==0} {
	# remarque ($ancienMode(cost)==0) || ($cost ==0) signfie que l'un des deux modes n'est pas cost
	if {($ancienMode(cost) != $cost) && ( ($ancienMode(cost)==0) || ($cost ==0))} {
	    checkDejaOuvert
        }
	validControl $w $c

    } else {
	set cost $ancienMode(cost)
    }
}

proc validControlPN {w c} {
    global scheduling allowedArc outFormat parameters typePN computOption cost controle
    global simulatorOn
    global ancienMode
    global modif
    global tpn tabUnDo

    if {$simulatorOn==0} {
	if {$controle > 0} {set cost 0}
	if {($ancienMode(controle) != $controle) && ( ($ancienMode(controle)==0) || ($controle ==0))} {
	    checkDejaOuvert
        }
	validControl $w $c
    } else {
	set controle $ancienMode(controle)
    }
}


proc validControl {w c} {
    global  allowedArc outFormat typePN parameters computOption cost controle
    global simulatorOn
    global ancienMode 
    global modif
    global tpn tabUnDo 
    global avecDeveloppementEncours

#    puts "controle = $controle ; cost =$cost ; parameters = $parameters; typePB = $typePN"
#    if {$parameters == 2} {
#      set hullOk "active"
#    } else {	
#       set hullOk "disabled"
    #    }
    if {$simulatorOn==0} {
      if {$controle>=1} {
	  .control.frame.cost.costNo  configure -state disabled
	  .control.frame.cost.costYesHybrid  configure -state disabled
	  .control.frame.cost.costYesSplit  configure -state disabled
	  if {$typePN==-2} { set typePN 1}

	  if { $controle==1} {
	      set typePN 0
#	      .control.frame.optionTPN.define configure -state disabled
	      .control.frame.parametre.paramNo configure -state disabled
	      .control.frame.parametre.paramYes configure -state disabled
	      .control.frame.parametre.paramInt configure -state disabled
	      .control.frame.parametre.paramUnder configure -state disabled

	     .control.frame.optionTPN.ttpn configure -state disabled
	     .control.frame.optionTPN.stopwatch configure -state disabled
#	     .control.frame.optionTPN.schedule configure -state disabled
	     .control.frame.optionTPN.hybrid configure -state disabled
	  } else {
	      if {$typePN==0} {
		  set typePN 1
		  .control.frame.optionTPN.pn configure -state disabled
	      }
		  
#	      .control.frame.optionTPN.define configure -state disabled
	      .control.frame.parametre.paramNo configure -state active
	      .control.frame.parametre.paramYes configure -state active
	      .control.frame.parametre.paramInt configure -state active
	      .control.frame.parametre.paramUnder configure -state active

	     .control.frame.optionTPN.ttpn configure -state active
	     .control.frame.optionTPN.stopwatch configure -state active
#	     .control.frame.optionTPN.schedule configure -state disabled
	     .control.frame.optionTPN.hybrid configure -state active
	 }

#	  $w.barreHaut.simulate configure -state disabled
         
#	  $w.barreHaut.simulate configure -state disabled



      } elseif {($ancienMode(controle) != $controle) } {

	  
	  .control.frame.optionTPN.pn configure -state active
	  .control.frame.optionTPN.ttpn configure -state active
	  .control.frame.optionTPN.stopwatch configure -state active
#	      .control.frame.optionTPN.schedule configure -state active
	  .control.frame.optionTPN.hybrid configure -state active
	  if {$typePN!=0} {
	      .control.frame.cost.costNo  configure -state active
	      .control.frame.cost.costYesHybrid  configure -state active
	      .control.frame.cost.costYesSplit  configure -state active
	  }
	      $w.barreHaut.simulate configure -state active

      }

	if { (($ancienMode(typePN) != $typePN) || ($ancienMode(parameters) != $parameters) || ($ancienMode(cost) != $cost) || (($ancienMode(controle) != $controle))) } {

	    # -1 : stopwatch ;   -2 scheduling ; -3 hybrid ; 0 PN ; 1 t-tpn ; 2 p-tpn
	   if {$typePN==-1} {
		    if {$allowedArc(timedInhibitor) ==0} {
			set allowedArc(timedInhibitor) 1
			destroy $w.barreGauche.p
			destroy $w.barreGauche.seph
			creerBarreDessin $w $c
		    }
	            if {$parameters>1} {set parameters 1 }
#		    .control.frame.optionTPN.define configure -state disabled
		    .control.frame.parametre.paramNo configure -state active
		    .control.frame.parametre.paramYes configure -state active
		    .control.frame.parametre.paramInt configure -state disabled
		    .control.frame.parametre.paramUnder configure -state disabled
#		    .control.frame.parametre.integer.hull.nofull configure -state $hullOk
#		    .control.frame.parametre.integer.hull.full configure -state $hullOk

	   } elseif {$typePN==-2} {
		    if {$allowedArc(timedInhibitor) ==1} {
			set allowedArc(timedInhibitor) 0
			destroy $w.barreGauche.p
			destroy $w.barreGauche.seph
			creerBarreDessin $w $c
		    }
#		    .control.frame.optionTPN.define configure -state active
	            if {$parameters>1} {set parameters 1 }
		    .control.frame.parametre.paramNo configure -state active
		    .control.frame.parametre.paramYes configure -state active
		    .control.frame.parametre.paramInt configure -state disabled
		    .control.frame.parametre.paramUnder configure -state disabled
	   } elseif {$typePN==-3} {
		    if {$allowedArc(timedInhibitor) ==0} {
			set allowedArc(timedInhibitor) 1
			destroy $w.barreGauche.p
			destroy $w.barreGauche.seph
			creerBarreDessin $w $c
		    }
	            if {$parameters>1} {set parameters 1 }
#		    .control.frame.optionTPN.define configure -state disabled
		    .control.frame.parametre.paramNo configure -state active
		    .control.frame.parametre.paramYes configure -state active
		    .control.frame.parametre.paramInt configure -state disabled
		    .control.frame.parametre.paramUnder configure -state disabled
#		    .control.frame.parametre.integer.hull.nofull configure -state disabled
#		    .control.frame.parametre.integer.hull.full configure -state disabled
	   } elseif {$typePN==1} {
		    if {$allowedArc(timedInhibitor) ==1} {
			set allowedArc(timedInhibitor) 0
			destroy $w.barreGauche.p
			destroy $w.barreGauche.seph
			creerBarreDessin $w $c
		    }
 #		    .control.frame.optionTPN.define configure -state disabled
	            .control.frame.parametre.paramNo configure -state active
	            .control.frame.parametre.paramYes configure -state active
	            .control.frame.parametre.paramInt configure -state active
	            .control.frame.parametre.paramUnder configure -state active
		    
#		    .control.frame.parametre.integer.hull.nofull configure -state $hullOk
#		    .control.frame.parametre.integer.hull.full configure -state $hullOk
	   } elseif {$typePN==0} {
		    if {$allowedArc(timedInhibitor) ==1} {
			set allowedArc(timedInhibitor) 0
			destroy $w.barreGauche.p
			destroy $w.barreGauche.seph
			creerBarreDessin $w $c
		    }
		    set parameters 0
		    .control.frame.parametre.paramNo configure -state disabled
		    .control.frame.parametre.paramYes configure -state disabled
		    .control.frame.parametre.paramInt configure -state disabled
		    .control.frame.parametre.paramUnder configure -state disabled

	            .control.frame.cost.costNo  configure -state disabled
	            .control.frame.cost.costYesHybrid  configure -state disabled
	            .control.frame.cost.costYesSplit  configure -state disabled
	       
	   }


   	   if {($typePN==1)&&($parameters>=0)&&($controle==0)} {
	       .control.frame.cost.costNo  configure -state active
	       .control.frame.cost.costYesHybrid  configure -state active
	       .control.frame.cost.costYesSplit  configure -state active
	   } elseif  {($typePN==-1)&&($parameters<=1)&&($controle==0)} {
	       if {$cost>1} {set cost 1 }
	       .control.frame.cost.costNo  configure -state active
#	       .control.frame.cost.costYesGlobal  configure -state active
	       .control.frame.cost.costYesHybrid  configure -state active
#	       .control.frame.cost.costYesOptim  configure -state active
	       .control.frame.cost.costYesSplit  configure -state disabled
	   } else {
	       if {$cost>0} {set cost 0 }
	       .control.frame.cost.costNo  configure -state disabled
#	       .control.frame.cost.costYesGlobal  configure -state disabled
	       .control.frame.cost.costYesHybrid  configure -state disabled
#	       .control.frame.cost.costYesOptim  configure -state disabled
	       .control.frame.cost.costYesSplit  configure -state disabled
	   }
   
	   if {($ancienMode(parameters)!=$parameters)&&(($ancienMode(parameters)==0)||($parameters==0))} {
	       heriterContrainteTempo $parameters $tpn(courant)
	       checkDejaOuvert
	   }

	    save_preferences
	    menuHaut $w $c 0
	    MAJdessinsProjetcourant $w 
  	    queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0            
       }
	set ancienMode(typePN) $typePN 
	set ancienMode(parameters) $parameters
	set ancienMode(cost) $cost
	set ancienMode(controle) $controle
    } else {
	# inutile ?
	set typePN $ancienMode(typePN)
    }
    
}

