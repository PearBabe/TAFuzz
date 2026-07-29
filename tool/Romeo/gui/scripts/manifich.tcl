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

 # procedure aide
# procedure imprime
# procedure quitter
# procedure aiguillageEnregistrer, enregistrerSous, enregistrerTpnXml
# procedure compilerRDP, verifSem,
# procedures diverses : tailleX, tailleY, sansEspace, slach, parcourir, repertoire, nomSeul

# les procedures associées au lancement du calcul du GDC comme fautIlSauver, calculGDC, calculQuiGDC sont dans stateSpace.tcl

# Rappel  TypeArc 0 = PlaceTransition  ---  1 = flush --- 2 = read --- 3 = logicalInhibitor, --- otherwise 4 = timedInhibitor
     


#*******************************HELP*********************************** 


proc aide {} { 
    global francais 
    global versionRomeo 
 


    set help .fenetreAide 
    catch {destroy $help} 
    toplevel $help 
     
    wm title $help [mc "Romeo Help"] 
     
    text $help.text -yscrollcommand "$help.scroll set" -setgrid true \
	-width 130 -height 50 -wrap word -bg white -font fontEditor
    scrollbar $help.scroll -command "$help.text yview" 
     
    pack $help.scroll -side right -fill y 
     
    pack $help.text -expand yes -fill both 
    $help.text tag configure rouge -foreground red 
    $help.text tag configure bleu -foreground blue 
    $help.text tag configure surgris -background #a0b7ce 
    $help.text tag configure souligne -underline on 
 
 
	#******************** en anglais****************** 
	$help.text insert end "$versionRomeo \n\n This version performs : \n"
	$help.text insert end " - on-the-fly verification of TCTL properties \n - simulation \n\n" bleu

	$help.text insert end "on the following extensions of T-Time Petri nets:\n"
	$help.text insert end " - TPN : Time Petri nets with reset arcs, read arcs and logical inhibitor arcs \n - SwPN : Stopwatch TPN (ie with timed inhibitor arcs),\n - Parametric extension of TPN and SwPN \n" bleu
	$help.text insert end " - Cost time Petri nets\n" bleu

	$help.text insert end " - High Level time Petri nets\n" bleu
   	$help.text insert end "Precondition (guard) and post-condition (update) over a set of state variables (X) are associated with transitions. A transition is enabled if there are enough tokens in its input places and if the guard is true. When the transition fires the corresponding updates are executed modifying the values of the state variables.\n Guards are boolean expressions over X and updates can be described as a sequence of imperative code expressed in a C-like language but whose execution is atomic from the transition firing point of view. \n" 
    $help.text insert end "   * Guards" bleu
        $help.text insert end " are boolean expressions over X. \n" 
    $help.text insert end "   * Updates" bleu
        $help.text insert end " can be described as a sequence of C-like code (including function call)  whose execution is atomic from the transition firing point of view. \n" 

    $help.text insert end "   * Variables" bleu
       $help.text insert end " are declared in the " 
       $help.text insert end "Declaration" surgris
       $help.text insert end " bloc of the Petri Net Tab by: "
       $help.text insert end "initially \{...X declaration and initialization ..\}\n" bleu
    $help.text insert end "   * Functions" bleu
    $help.text insert end " are declared in the " 
       $help.text insert end "Declaration" surgris
       $help.text insert end " bloc of the Petri Net Tab. \n "
    $help.text insert end "  * External files" bleu
       $help.text insert end " of functions can be included in the "
    $help.text insert end "Project" surgris
    $help.text insert end " bloc of the Petri Net Tab.  \n\n" 
   

    	$help.text insert end " - Colored time Petri nets (or SWPN) \n" bleu
   	$help.text insert end "The tokens have a color and the arcs can filter the colors that enable the transition. If a transition is enabled by several colors then as many clocks are associated with the transition for the measurement of the enabling time."

   	$help.text insert end "\n\n"

	$help.text insert end " \n Moreover this version also performs : \n"
	$help.text insert end " - Optimal reachability for cost time Petri nets\n" bleu
	$help.text insert end " - Parameter synthesis for Parametric extension of TPN and SwPN \n" bleu
	$help.text insert end " - Controller synthesis for untimed control Petri nets \n\n" bleu

#  - computation of the State Class Graph of Time Petri Nets  \n 
#  - computation of the State Class (Timed) Automaton of Time Petri Nets (Uppaal or Kronos input formats). This timed automaton and the TPN are timed bisimilar.\n
#  - computation of the Zone-Based Graph that preserve either markings or LTL temporal properties\n
#  - computation of the Marking (Timed) Automaton of Time Petri Nets (Uppaal input formats). This timed automaton and the TPN are timed bisimilar.\n 
#  - structural translation from Time Petri Nets to Timed Automata (Uppaal input format). This timed automaton and the TPN are timed bisimilar.\n 
#	$help.text insert end " (and thanks the Uppaal DBM library) :\n
#	$help.text insert end "On stopwatch Time Petri nets (scheduling-TPN or TPN with timed inhibitor arcs) :" souligne   
#	$help.text insert end "\n 
# - overapproximation (with DBM) of the computation of the extended State Class Graph of TPN\n 
#  - exact computation (thanks to Parma Polyhedra Library) of the extended State Class Graph of scheduling-TPN (TEXT, MEC or Aldebaran formats)\n 
#  - exact computation with both DBM and polyhedra of the extended State Class Graph of scheduling-TPN \n 
#  - computation of the State Class stopwatch automaton (Hytech input format). This stopwatch automaton and the scheduling-TPN are timed bisimilar \n
#  - on-the-fly verification of TCTL properties \n 
#  - simulation \n\n" 
#	$help.text insert end "On parametric Petri nets (PTPN or scheduling-PTPN or PTPN with timed inhibitor arcs) :" souligne   
#  - exact computation (thanks to Parma Polyhedra Library) of the parametric State Class Graph\n 
#	$help.text insert end "\n 
#  - on-the-fly verification of parametric TCTL properties \n
#  - parametric simulation. \n\n"  

	$help.text insert end "
                                               HELP                                                 " souligne 
	$help.text insert end "\n \n" 
	$help.text insert end "A. To create the net :" souligne 
	$help.text insert end "\n \n A.1) In the "
	$help.text insert end "control panel" surgris 
	$help.text insert end "\n     -Select TPN type (TPN or stopwatch-TPN (i.e. TPN with timed inhibitor arcs) or Hybrid) or Untimed Control PN"
#	$help.text insert end "\n     -Select  output formats in the " 
	$help.text insert end "\n     -Valid allowed logical arcs (read, reset and logical inhibitor arcs) " 
	$help.text insert end "\n \n A.2) Create places/arcs/transitions with " 
	$help.text insert end "Edit" surgris 
	$help.text insert end " menu (or " 
	$help.text insert end "right-click" rouge 
	$help.text insert end ") \n \n A.3) Go back to " 
	$help.text insert end "selection" surgris 
	$help.text insert end " mode with the button (or " 
	$help.text insert end "Escape" rouge 
	$help.text insert end ")\n \n" 
	$help.text insert end " A.4) Give places, arcs and transitions characteristics (with " 
	$help.text insert end "right-click or double-click" rouge 
	$help.text insert end ") \n \n A.5) " 
	$help.text insert end "Save" surgris 
	$help.text insert end " TPN " 
	$help.text insert end "          -> file.xml  \n \n \n" bleu 
	$help.text insert end "B. Manipulate variable :" souligne 
	$help.text insert end "\n \n B.1) Declare the set X of variables in the " 
	$help.text insert end "Declaration" surgris 
	$help.text insert end " bloc (using C-like syntax) of the Petri Net Tab: "
    $help.text insert end "initially \{...X declaration and initialization ..\}" bleu
$help.text insert end "     \n \n B.2) Declare Types and Functions in the " 
	$help.text insert end "Declaration" surgris 
    $help.text insert end " bloc (using C-like syntax) of the Petri Net Tab. \n"
        $help.text insert end " External files" bleu
       $help.text insert end " of functions can be included in the "
    $help.text insert end "Project" surgris
    $help.text insert end " bloc of the Petri Net Tab.  " 
    $help.text insert end "\n\n B.3) Declare Enabling condition of transitions in the Guard (with " 
	$help.text insert end "right-click or double-click" rouge 
    $help.text insert end " on transitions):"

#   	$help.text insert end "Let X the set of variables declared in the " 
#   	$help.text insert end "Declaration" surgris
#    	$help.text insert end " bloc of the Petri Net Tab: "
#  	$help.text insert end "initially \{...X declaration and initialization ..\}" bleu
    
#	$help.text insert end " We first define a linear expression over the set X of variables declared in the " 
 #       $help.text insert end "Declaration" surgris
#        $help.text insert end " bloc: \n \n"
        $help.text insert end " \n \n"
        $help.text insert end "Linear expression over X =" surgris
        $help.text insert end "  a*x  \| p op q   " bleu
        $help.text insert end " where \n"
        $help.text insert end "  x    " rouge
        $help.text insert end " is in X ; \n" 
        $help.text insert end "  a    " rouge
        $help.text insert end " is a positive or negative integer coefficient ; \n" 
        $help.text insert end "  op   " rouge
        $help.text insert end " is in \{+,-\} ; \n" 
        $help.text insert end "  p,q  " rouge
        $help.text insert end " are linear expressions over X ;\n \n "
	$help.text insert end " A guard of a transition must be of the form: \n\n"

        $help.text insert end "Guard =" surgris
        $help.text insert end "  lexp ~ k \| u lop v   " bleu
        $help.text insert end " with \n"
        $help.text insert end "  lexp" rouge
        $help.text insert end "  is a linear expression over X  \n" 
        $help.text insert end "  k    " rouge
        $help.text insert end " is positive or negative integer ; \n" 
        $help.text insert end "  ~    " rouge
        $help.text insert end " is a comparison operator in \{<,<=, >, >=, ==, !=\} ; \n"
        $help.text insert end "  lop  " rouge
        $help.text insert end " is in \{and,or\} ; \n" 
        $help.text insert end "  u,v  " rouge
        $help.text insert end " are guards ; \n"
#        $help.text insert end "Example: x < 3 and x-2*y==4 and 3*x+z>=8 \n" 
#        $help.text insert end "If x=-2, y=-3 and z =20 then the guard is true\n"

	$help.text insert end " \n B.4) Declare Updates (on variables) performed by the firing of transitions (with " 
	$help.text insert end "right-click or double-click" rouge 
	$help.text insert end " on transitions) \n\n"
	$help.text insert end " An update of a transition must be of the form: \n\n"
        $help.text insert end "Update =" surgris
        $help.text insert end "  x = f ; \| x = g ;  \| p q   " bleu
        $help.text insert end " with \n"
        $help.text insert end "  x    " rouge
        $help.text insert end " is in the set X of variables declared in the " 
        $help.text insert end "Declaration" surgris
        $help.text insert end " bloc ; \n" 
        $help.text insert end "  f    " rouge
        $help.text insert end " is a linear expression over the set X ; \n" 
        $help.text insert end "  g    " rouge
        $help.text insert end " is a function declared in the "
        $help.text insert end "Declaration" surgris
        $help.text insert end " bloc or in external file of the project ; \n" 
        $help.text insert end "  p,q  " rouge
        $help.text insert end " are updates ;\n \n"
        $help.text insert end "Note that p and q will be executed sequentially (p before q) and the update of a transition is atomic from its firing point of view. \n\n\n" 

	$help.text insert end "C. Parametric PN :  parametric TPN or parametric stopwatch PN :" souligne 
	$help.text insert end "\n \n C.1) In parametric-PN box in the " 
	$help.text insert end "Control panel" surgris 
	$help.text insert end "\n Select the class of parameters (real or integer) \n Note that (theoretical) termination of model checking is guarantee only with integer (and bounded) parameters" 
	$help.text insert end "\n \n C.2)  Give the parametric timed constraint of each transition  (with " 
	$help.text insert end "right-click or double-click" rouge 
	$help.text insert end " on transitions) \n \n A Parametric Timed Constraint of a transition is a linear expression over the set Par of parameters"
#        $help.text insert end "ParametricConstraint =" surgris
#        $help.text insert end "   a*p \| p*a \| p op p'   " bleu
#        $help.text insert end " with \n"
#        $help.text insert end "  p " rouge
#        $help.text insert end " is a parameter \n" 
#        $help.text insert end "  a  " rouge
#        $help.text insert end " is a positive or negative integer coefficient ; \n" 
#        $help.text insert end "  op " rouge
#        $help.text insert end " is in \{+,-\} ; \n" 
	$help.text insert end "\n \n C.3) Give the global parametric constraints of the net in menu " 
	$help.text insert end "Parametric-PN" surgris 
	$help.text insert end " -> Constraints on parameters \n\n"
	$help.text insert end " Global parametric timed Constraint must be of the form: \n\n"
        $help.text insert end "GlobalConstraint =" surgris
	$help.text insert end " ptc1 ~ ptc2 " bleu
	$help.text insert end " where \n"
        $help.text insert end "  ptc1, ptc2" rouge
        $help.text insert end " are parametric timed constraints \n" 
        $help.text insert end "  ~    " rouge
        $help.text insert end "      is a comparison operator in \{<,<=, >, >=, ==\} ; \n\n\n" 


	$help.text insert end "D. Colored TPN (or SwPN) :" souligne 
    $help.text insert end "\n \n D.1) In "
    $help.text insert end "Project" surgris
    $help.text insert end " bloc of the Petri Net Tab, select colored PN and choose and validate the number of colors." 
	$help.text insert end "\n \n D.2)  With " 
	$help.text insert end "right-click or double-click" rouge 
	$help.text insert end " on arcs, choose the allowed color.\n If"
	$help.text insert end " Any" bleu
	$help.text insert end " is selected then all colors are allowed for this arc.\n If" 
	$help.text insert end " Any" bleu
    $help.text insert end " is selected for several arcs of a given transition, the same value of color is applied for these arcs. \n "
    	$help.text insert end "  If a transition is enabled by several colors then as many clocks are associated with the transition for the measurement of the enabling time."
	$help.text insert end "\n \n D.3)  The variable "
    	$help.text insert end " \$any" bleu
    	$help.text insert end "  can be used as a parameter in the update of the transition. It gives the value of the color used for the firing of the transition. \n\n\n"

    $help.text insert end "E. Cost PN : " souligne 
	$help.text insert end "\n \n E.1) In cost-PN box in the " 
	$help.text insert end "Control panel" surgris 
	$help.text insert end "\n Select the way to compute the cost state classes" 
	$help.text insert end "\n \n E.2)  Give the discrete (integer) cost of each transition  (with " 
	$help.text insert end "right-click or double-click" rouge 
	$help.text insert end " on transitions)"
	$help.text insert end "\n \n E.3) Give the timed cost rate of the net in menu " 
	$help.text insert end "Cost-TPN" surgris 
	$help.text insert end " -> Timed Cost \n"
	$help.text insert end "The timed cost rate is a linear expression over the set of Places.\n\n\n" 


	$help.text insert end "F. Untimed control PN : " souligne 
	$help.text insert end "\n \n F.1) In Untimed control PN box in the " 
	$help.text insert end "Control panel" surgris 
	$help.text insert end "\n click on the button" 
	$help.text insert end "\n \n F.2)  Select control attributes of each transition  (with " 
	$help.text insert end "right-click or double-click" rouge 
	$help.text insert end " on transitions) :\n       ->"
	$help.text insert end " Controlable, Uncontrolable, Avoidable, Ineluctable." bleu

#
#	$help.text insert end "B. On the underlying Petri net  :" souligne 
#	$help.text insert end "\n \n B.1)  Create PN (TPN or scheduling-TPN) \n \n B.2) menu : " 
#	$help.text insert end "PN" surgris 
#	$help.text insert end " Compute the marking graph (Select the format in the control panel) :\n \n" 
#	$help.text insert end "        - text     "  
#	$help.text insert end "-> file-untimed.txt \n \n" bleu 
#	$help.text insert end "C. On time Petri nets (TPN) :" souligne 
#	$help.text insert end "\n \n C.1) Translate (structural translation) Time Petri Net to Timed Automata :"  
#	$help.text insert end "\n \n     Menu " 
#	$help.text insert end "TPN" surgris 
#	$help.text insert end " : Structural translation to  Timed Automata (UPPAAL input format) " 
#	$help.text insert end "    -> choose-file-name.xta \n \n \n" bleu 
#	$help.text insert end " C.2) To compute the State Class Graph of a TPN (Select the format in the control panel) :"  
#	$help.text insert end "\n \n     Menu : " 
#	$help.text insert end "TPN" surgris 
#	$help.text insert end " : state Class Graph "  
#	$help.text insert end "with formats "  
#	$help.text insert end " :\n \n"  
#	$help.text insert end "        - text     "  
#	$help.text insert end " -> file-scg.txt \n \n" bleu 
#	$help.text insert end " C.3) To compute the Zone based Graph of a TPN (Select the format in the control panel) :"  
#	$help.text insert end "\n \n     Menu : " 
#	$help.text insert end "TPN" surgris 
#	$help.text insert end " : Zone Based Graph "  
#	$help.text insert end "preserving marking (inclusion)  "  
#	$help.text insert end " :\n \n"  
#	$help.text insert end "        -> file-ma.   \n \n" bleu 
#	$help.text insert end "\n    Menu : " 
#	$help.text insert end "TPN" surgris 
#	$help.text insert end " : Zone Based Graph preserving LTL  "  
#	$help.text insert end " :\n \n"  
#	$help.text insert end "        -> file-zbg.   \n \n" bleu 
#	$help.text insert end " C.4) To compute the State Class Timed Automaton of a TPN (Select the format in the control panel):"  
#	$help.text insert end "\n \n     Menu :" 
#	$help.text insert end "TPN" surgris 
#	$help.text insert end " : State Class Timed Automaton "  
#	$help.text insert end " with formats :"  
#	$help.text insert end "\n \n       - UPPAAL : no clock renaming " 
#	$help.text insert end "  -> file-scta.xta " bleu 
#	$help.text insert end "\n \n  \n" 
#	$help.text insert end " C.5) To compute the Marking Timed Automaton of a TPN (Select the format in the control panel):"  
#	$help.text insert end "\n \n     Menu " 
#	$help.text insert end "TPN" surgris 
#	$help.text insert end " : Marking Timed Automaton "  
#	$help.text insert end " with formats :"  
#	$help.text insert end "\n \n       - UPPAAL " 
	$help.text insert end " \n \n \n" 
	$help.text insert end "G. To check TCTL property on the net (on the fly model checking) :"  souligne
	$help.text insert end "\n \n     Use the " 
	$help.text insert end "Check" surgris 
	$help.text insert end " button to edit and check the property "  
	$help.text insert end "\n \n \n" 
	$help.text insert end "H. TPN Simulation :"  souligne
	$help.text insert end "\n \n Use the " 
	$help.text insert end "Simulate" surgris 
	$help.text insert end " button \n Select zone based or state class based computation" 
	$help.text insert end "\n Click on the transition you want to fire "  
	$help.text insert end "\n \n \n" 
#	$help.text insert end "D. On stopwatch TPN :  scheduling-TPN or TPN with timed inhibitor arcs :" souligne 
#	$help.text insert end "\n \n D.1) In the " 
#	$help.text insert end "Control panel" surgris 
#	$help.text insert end " : select " 
#	$help.text insert end "scheduling-TPN" surgris 
#	$help.text insert end " or " 
#	$help.text insert end "stopwatch-PN (timed inhibitor arcs)" surgris 
#	$help.text insert end "\n \n D.2)  If scheduling-TPN then : \n         -" 
#	$help.text insert end "Define scheduler" surgris 
#	$help.text insert end ",\n         -create the scheduling-TPN, \n" 
#	$help.text insert end "         -and give characteristics : " 
#	$help.text insert end "processor" surgris 
#	$help.text insert end " and " 
#	$help.text insert end "priority" surgris 
#	$help.text insert end " of places \n \n D.3) State space computation (Select the format in the control panel)" 
#	$help.text insert end "\n \n     Menu " 
#	$help.text insert end "stopwatch-PN" surgris 
#	$help.text insert end " :\n \n      * Overapproximation of the extended state class graph with formats :\n \n"
#	$help.text insert end "      -> file-scg.  \n \n" bleu
#	$help.text insert end "      * Exact computation (polyhedra) of the extended state class graph with formats :\n \n"  
#	$help.text insert end " -> file-scg.  \n \n" bleu
#	$help.text insert end "      * Exact computation (DBM+polyhedra) of the extended state class graph with formats :\n \n"
#	$help.text insert end " -> file-scg.  \n \n" bleu
#	$help.text insert end "        * Extended State class stopwatch automaton \n \n " 
#	$help.text insert end "      -> file-scswa.hy \n \n \n" bleu
#	$help.text insert end " D.4) To check TCTL property on the net (on the fly model checking) :"  
#	$help.text insert end "\n \n     Use the " 
#	$help.text insert end "Check" surgris 
#	$help.text insert end " button to edit and check the property "  
#	$help.text insert end "\n \n \n" 
#	$help.text insert end " D.5) stopwatch-PN simulation :"  
#	$help.text insert end "\n \n     Use the " 
#	$help.text insert end "Simulate" surgris 
#	$help.text insert end " button and click on the transition you want to fire "  
#	$help.text insert end "\n \n \n" 

#	$help.text insert end "\n \n E.4) Parametric State space Computation :" 
#	$help.text insert end "\n \n     Menu " 
#	$help.text insert end "stopwatch-PN" surgris 
#	$help.text insert end " ->    parametric state class graph \n \n E.5)"  
#	$help.text insert end " \n E.4) To check parametric TCTL property on the net :"  
#	$help.text insert end "\n \n     Use the " 
#	$help.text insert end "Check" surgris 
#	$help.text insert end " button to edit and check the property\n\n "
#	$help.text insert end "          * define a"
#	$help.text insert end " maximum trace size" surgris
#	$help.text insert end "(by default 0 if none):\n"
#	$help.text insert end "            stop the computation and return an approximated result (sufficient condition)"
#	$help.text insert end "\n \n \n" 
#	$help.text insert end " E.6) TPN Simulation :"  
#	$help.text insert end "\n \n     Use the " 
#	$help.text insert end "Simulate" surgris 
#	$help.text insert end " button and click on the transition you want to fire "  
	$help.text insert end "\n \n \n" 
	 
	 
	 
} 
 
 
#*************************************IMPRIMER*********************************************** 
 
proc imprimer {w c} { 
    global nomRdP 
    global tpn tabUnDo
    global format 
    global rotation 
    global reduction 
    global francais 
    global zoom 
 
    set oui 1 
 
    if { ![string compare "$nomRdP($tpn(onglet))" "noName.xml"]}  { 
        set reponse [tk_messageBox -message [mc "Save net before PostScript export?"] -type yesnocancel -icon question -font menufont] 
	switch -exact $reponse { 
	    cancel { set oui 0 } 
	    yes {  enregistrerSousRdP $w } 
	} 
    } 
 
    if {$oui==1} { 
	set last [string first ".xml" "$nomRdP($tpn(onglet))"] 
 
	if {$last>=0} {set nomPs [string range "$nomRdP($tpn(onglet))" 0 [expr $last -1]]} else { set nomPs $nomRdP($tpn(onglet))} 
 
	set format  1 
	set rotation 0 
	set reduction 0 
 
	queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0 
 
	set fi .fenetreImprimer 
	catch {destroy $fi} 
	toplevel $fi 
	wm title $fi [format [mc "Creating PostScript file %s.ps"] $nomRdP($tpn(onglet))] 
	bind $fi <Return> "validerParametreImpression $nomPs $fi $c" 
 
	frame $fi.buttons 
	pack $fi.buttons -side bottom -fill x -pady 2m 
	button $fi.buttons.annuler -text [mc "Cancel"] -command  "destroy $fi" 
	button $fi.buttons.accepter -text [mc "Ok"]  \
	    -command "validerParametresImpression {$nomPs} $fi $c" 
	pack $fi.buttons.accepter $fi.buttons.annuler  -side left -expand 1 
 
 
 
	frame $fi.parametres 
	pack $fi.parametres  -side left -expand yes -fill y  -pady .5c -padx .5c 
 
	label $fi.parametres.label -text [mc "Parameters: "] 
	pack $fi.parametres.label -side top 
 
	frame $fi.parametres.sep -relief ridge -bd 1 -height 2 
	pack $fi.parametres.sep -side top -fill x -expand no 
 
	# **************** bouton de format (A4 A5) et de rotation (portrait paysage)*********************** 
 
	radiobutton $fi.parametres.option1 -text "A4" -variable format \
	    -relief flat  -value 1  -width 20 -anchor w 
	radiobutton $fi.parametres.option2 -text "A5" -variable format \
	    -relief flat  -value 2  -width 20 -anchor w 
	radiobutton $fi.parametres.portrait -text [mc "Portrait"] -variable rotation\
	    -relief flat  -value 0  -width 20 -anchor w 
	radiobutton $fi.parametres.paysage -text [mc "Landscape"] -variable rotation\
	    -relief flat  -value 1  -width 20 -anchor w 
 
 
	pack $fi.parametres.option1  -side top -pady 2 -anchor w -fill x 
	pack $fi.parametres.option2  -side top -pady 2 -anchor w -fill x 
	pack $fi.parametres.portrait  -side top -pady 2 -anchor w -fill x 
	pack $fi.parametres.paysage  -side top -pady 2 -anchor w -fill x 
 
 
	# **************************** bouton de reduction ************************************** 
 
	frame $fi.reduction 
	pack $fi.reduction  -side left -expand yes -fill y  -pady .5c -padx .5c 
 
	label $fi.reduction.label -text [mc "Reduction: "] 
	pack $fi.reduction.label -side top 
 
	frame $fi.reduction.sep -relief ridge -bd 1 -height 2 
	pack $fi.reduction.sep -side top -fill x -expand no 
 
 
	radiobutton $fi.reduction.option0 -text [mc "Automatic"] -variable reduction \
	    -relief flat  -value 0  -width 20 -anchor w 
	radiobutton $fi.reduction.option200 -text "200 %" -variable reduction \
	    -relief flat  -value 0.5  -width 20 -anchor w 
 
	radiobutton $fi.reduction.option1 -text "100 %" -variable reduction \
	    -relief flat  -value 1  -width 20 -anchor w 
 
	radiobutton $fi.reduction.option2 -text "75 %" -variable reduction\
	    -relief flat  -value 1.5  -width 20 -anchor w 
 
	radiobutton $fi.reduction.option3 -text "50 %" -variable reduction\
	    -relief flat  -value 2  -width 20 -anchor w 
 
	radiobutton $fi.reduction.option4 -text "25 %" -variable reduction \
	    -relief flat  -value 4  -width 20 -anchor w 
	radiobutton $fi.reduction.option5 -text "10 %" -variable reduction \
	    -relief flat  -value 10  -width 20 -anchor w 
 
	pack $fi.reduction.option0  -side top -pady 2 -anchor w -fill x 
	pack $fi.reduction.option200  -side top -pady 2 -anchor w -fill x 
	pack $fi.reduction.option1  -side top -pady 2 -anchor w -fill x 
	pack $fi.reduction.option2  -side top -pady 2 -anchor w -fill x 
	pack $fi.reduction.option3  -side top -pady 2 -anchor w -fill x 
	pack $fi.reduction.option4  -side top -pady 2 -anchor w -fill x 
	pack $fi.reduction.option5  -side top -pady 2 -anchor w -fill x 
 
    } 
 
    #12 et 13 normal 
 
    #************************ procedure de validation des parametres d'impression ***************** 
 
    proc validerParametresImpression {nomPs laFenetre c} { 
	global format 
	global rotation 
	global reduction 
	global maxX maxY 
	global zoom 
	global tpn tabUnDo

 
	affiche "\n" 
#	affiche [format [mc "-Exporting net to PostScript file: %s.ps ..."] $nomPs] 
	affiche [mc "-Exporting net to PostScript file: "] 
        afficheBleu "$nomPs\.ps" 
	affiche " ..." 
	 
	set sauvZoom $zoom 
	set zoom 1 
	redessinerRdP $c 
	 
	set x [expr [tailleX]+50] 
	set y [expr [tailleY]+50] 
	set depassement 0 
 
	if {$reduction > 0} { 
 
	    set largeur [expr $x/$reduction] 
	    if {$rotation ==1} {set pa "nw"} else {set pa "sw"} 
	    #-pageanchor $pa                        -pagex 10 -pagey 10 -x 0 -y 0  \
 
	    $c postscript -file "$nomPs.ps" -height $y -width $x \
		-pagewidth $largeur \
		-x 0 -y 0 -rotate $rotation 
 
	    destroy $laFenetre 
	} else { 
	    #++++ c 'est a dire si reduction automatique +++++++++ 
 
 
	    set hauteur [expr (30-10*$rotation)/$format] 
	    set largeur [expr (20+10*$rotation)/$format] 
	    # calcul de la reduction de l'image : 
	    if { ($x/$largeur)<($y/$hauteur)} {set largeur [expr ($x*$hauteur)/$y]} 
	    set unit "c" 
	    set largeur $largeur$unit 
 
	    $c postscript -file "$nomPs.ps" -height $y -width $x \
		-pagewidth $largeur  \
		-x 0 -y 0 -rotate $rotation 
	    destroy $laFenetre 
 
	} 
	set zoom $sauvZoom 
	redessinerRdP $c 
	affiche [mc "done"] 
    } 
    #------ fin proc valider parametre d'impression 
} 
 
 
 
#***************************************QUITTER*************************************** 
 
proc quitterRdP {w} { 
    global nomRdP 
    global tpn tabUnDo
    global modif listeOnglets
    global francais 

    set oui 1 
    save_LastOpenFile $nomRdP($tpn(onglet))  
    for {set i 0} {$i<[llength $listeOnglets(tpn)]} {incr i} {
	if {$oui == 1} {
#            set tpn  [lindex $listeOnglets(tpn) $i]
            set leOnglet  [lindex $listeOnglets(indice) $i]
	    set tpnProvisoire [calculTPNdeOnglet $leOnglet]
            if {$modif($tpnProvisoire) ==1} { 
		if {[fautIlSauver]==0} {set oui 0} else {destroy $w.onglet.onglet$tpnProvisoire}
            } else {
                destroy $w.onglet.onglet$tpnProvisoire)
            }
	}
    }  
    if {$oui == 1} { 
	if {[winfo exists .fenetreCheck]} {
	    destroy .fenetreCheck
	}
	if {[winfo exists .fenetreSimul]} {
	    destroy .fenetreSimul
	}
	if {[winfo exists .control]} {
	    destroy .control
	}
	destroy .romeo
	destroy .
    } 
return 1
} 
 
#*******************************************NOUVEAU****************************************** 
 
proc nouveauRdP {w c} { 
    global tabPlace 
    global tabTransition 
    global declaration initialization timedCost nbTokenColor
    global tabConstraint
    global nbConstraints
    global nbProcesseur 
    global tpn tabUnDo 
    global nomRdP 
    global modif 
    global francais 
    global fin 
    global simulatorOn 
    global listeOnglets
     
    set oui 1 
    if {$simulatorOn==1} { 
	affiche "\n" 
	affiche [mc " -Warning: Not allowed - Quit simulator first"] 
	set oui 0      
    }
# elseif {$modif($tpn(courant)) ==1} { 
#	set reponse [tk_messageBox -message [mc "Save net?"] -type yesnocancel -icon question] 
#        switch -exact $reponse { 
#	    cancel { set oui 0 } 
#	    yes { 
#		if {[string compare "$nomRdP($tpn(onglet))" "noName.xml"]} { 
#		    enregistrerRdP "$nomRdP($tpn(onglet))" 
#		} else { 
#		    enregistrerSousRdP $w} 
#	    } 
#	} 
 #   } 


    if {($oui == 1)&&([existOnglets "noName.xml"]<0)} { 
        nouvelOnglet $w "noName.xml"       

	# nouvelOnglet met à jour tpn
	#        initialisation $c 
	set nbProcesseur($tpn(courant)) 0 
	set nomRdP($tpn(onglet)) "noName.xml" 
 
	# Statut des places : ok, detroy, ou fin 
	set tabPlace($tpn(courant),1,statut) $fin 
        set tabTransition($tpn(courant),1,statut) $fin 

	# Reinit constraints
	set tabConstraint($tpn(courant),0) ""
	set nbConstraints($tpn(courant)) 1
 
	set newFTP(transition) 0 
	set newFPT(place) 0 
#        redessinerRdP $c 
        queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0 
#        set nomRdP($tpn(onglet)) "noName.xml" 
#	$w.ligneDuBas.indication.nomRdp config -text [format [mc "Net: %s"] "$nomRdP($tpn(onglet))"] 
        set modif($tpn(courant)) 0 
	set declaration($tpn(courant)) "// insert here your type definitions using C-like syntax

// insert here your function definitions 
// using C-like syntax

initially \{

// insert here the state variables declarations 
// and possibly some code to initialize them 
// using C-like syntax
 
 \}

"
	set initialization($tpn(courant)) "// insert here the state variables declarations 
// and possibly some code to initialize them 
// using C-like syntax"

	set timedCost($tpn(courant))  ""
	set nbTokenColor($tpn(courant)) 0
			  
	if {[winfo exists $w.frame.c]} {
	    destroy $w.frame.c
	}
	if {[winfo exists $w.slave]} {
	    destroy $w.slave
	}

	canvasAsc $w $w.frame.c

    } 
} 
 
 
#******************************************* ENREGISTRER ****************************************** 
 
#+++++++++++++++++++++AIGUILLAGE+++++++++++++++++++++++++++ 
# enregistrer alors que nom = noName.xml 
 
proc aiguillageEnregistrer {w} { 
    global modif 
    global nomRdP projet
    global tpn tabUnDo timedCost nbTokenColor
    global francais 
    global simulatorOn 
    global synchronized
 
    set oui 1 
    if {$simulatorOn} { 
	set reponse [tk_messageBox -message [mc "The simulator is active. The net will be saved with its current marking. Continue?"] -type yesno -icon question] 
	switch -exact $reponse { 
	    yes {} 
	    no {set oui 0} 
	} 
    } 
     
    if {$oui} { 
	set tpn(courant) [calculTPNCourant 0]
	queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0 
	if {[string compare "$nomRdP($tpn(onglet))" "noName.xml"]} { 
	    enregistrerTpnXml $nomRdP($tpn(onglet)) 0
	} else { 
	    enregistrerSousRdP $w  
	} 

	set chemin [repertoire $nomRdP($tpn(onglet))]

	for {set i 1}  {$i<=$projet($tpn(onglet),nbInput)} {incr i} { 
	    if {$projet($tpn(onglet),input,$i,status)!="deleted"} {
		set tpn(courant) [calculTPNCourant $i]
		enregistrerTpnXml $chemin\/$projet($tpn(onglet),input,$i,file) $i
	    }
	}
	set tpn(courant) [calculTPNCourant 0]
    } 

} 
 
#+++++++++++++++++++++ ENREGISTRER SOUS +++++++++++++++++++++++++++ 
 
proc enregistrerSousRdP {w} { 
 
    global nomRdP 
    global tpn tabUnDo timedCost nbTokenColor
    global modif 
    global cheminFichiers 
    global francais 
    global simulatorOn 
    global synchronized
    global listeOnglets
 
    set oui 1 
    if {$simulatorOn} { 
	set reponse [tk_messageBox -message [mc "The simulator is active. The Petri net will be saved with current marking. Continue ?"] -type yesno -icon question] 
	switch -exact $reponse { 
	    yes {} 
	    no {set oui 0} 
	} 
    } 


    if {$oui} { 
	#   Type names      Extension(s)    Mac File Type(s) 
	# 
	#--------------------------------------------------------- 
	set types { 
	    {{[mc "File"]}     {.xml}      TEXT} 
	} 
	queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0 
 
	if [string compare "$nomRdP($tpn(onglet))" "noName.xml"] { 
	    set fichier [tk_getSaveFile -filetypes $types  -title [mc "Save net as"] \
			     -initialdir [repertoire $nomRdP($tpn(onglet))] -initialfile [nomSeul $nomRdP($tpn(onglet))] -defaultextension .xml] 
	} else { 
	    set fichier [tk_getSaveFile -filetypes $types  -title [mc "Save net as"] \
			     -initialdir "$cheminFichiers" -initialfile $nomRdP($tpn(onglet)) -defaultextension .xml] 
	     
	} 



	if [string compare $fichier ""] { 

	    #retirer l'espace du nom du fichier mais pas du repertoire
	    set lerep [repertoire $fichier]
	    set lefichier [sansEspace [nomSeul $fichier]]
	    set fichier "$lerep\/$lefichier"

	    if  {[existOnglets $fichier]>-1} {
#	    affiche "\n -An equivalent tab is already open" 
	    set button [tk_messageBox -icon error  -title "Save as... aborted" -message "An equivalent tab is already open" ] 

	    } else {

		enregistrerTpnXml $fichier 0
		set ancien $nomRdP($tpn(onglet))
#		set nomRdP($tpn(onglet)) $fichier 
		destroy $w.ligneDuBas.indication.nomRdp 
		label $w.ligneDuBas.indication.nomRdp 
		pack $w.ligneDuBas.indication.nomRdp -side left 
#	    $w.ligneDuBas.indication.nomRdp config -text [format [mc "Net: %s"] $nomRdP($tpn(onglet))] 
		set modif($tpn(courant)) 0 


		changeNameOngletCourant $w $fichier
	    }
	} 
    } 
} 
 
#+++++++++++++++++++++ GENERER FICHIER XML +++++++++++++++++++++++++++ 
 
proc enregistrerTpnXml {fichier esclave} { 
    global tabPlace tabTransition tabConstraint projet
    global declaration initialization
    global nbProcesseur tpn scheduling timedCost parameters nbTokenColor
    global fin ok 
    global modif versionRomeo
    global infini 
    global tabColor 
    global nbConstraints 
    global tpn tabUnDo
    global allowedArc
    global synchronized
 
    # toutCommeYFaut 
    if {$parameters>=1} {
	heriterContrainteTempo 0 $tpn(courant)
    } else {
	heriterContrainteTempo 1 $tpn(courant)
    }
 
     if {[winfo exists .declaration$tpn(onglet)]} {
	 valideclar .declaration$tpn(onglet) $tpn(onglet)
     }
     if {[winfo exists .initialization$tpn(onglet)]} {
	 valideIni .initialization$tpn(onglet) $tpn(onglet)
     }

    if {$scheduling==1} {set rien [verifSem 1]} 
 
    if [string compare $fichier ""] { 
	    affiche " \n" 
#	    affiche [format [mc "-Saving net as %s ..."] $fichier] 
	    affiche [mc "-Saving net as "] 
	    afficheBleu $fichier 
            affiche " ..." 
	    set File [open $fichier w] 
	    # ajout guillaume => histoire que les "parseurs" XML savent quoi "parser" 
	    puts $File "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>" 
	    puts $File "<romeo version=\"$versionRomeo\">" 
	    puts $File "<TPN name=\"$fichier\">" 
 
	    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} { 
		if {$tabPlace($tpn(courant),$i,statut)==$ok} { 
		    if {$tabPlace($tpn(courant),$i,dmax)==$infini} { 
			set lft "inf" 
		    } else { 
			set lft $tabPlace($tpn(courant),$i,dmax) 
		    } 
		    puts $File "  <place id=\"$i\" identifier=\"$tabPlace($tpn(courant),$i,id)\" label=\"$tabPlace($tpn(courant),$i,label,nom)\" initialMarking=\"$tabPlace($tpn(courant),$i,jeton)\" eft=\"$tabPlace($tpn(courant),$i,dmin)\" lft=\"$lft\"> 
      <graphics color=\"$tabPlace($tpn(courant),$i,color)\"> 
         <position x=\"$tabPlace($tpn(courant),$i,xy,x)\" y=\"$tabPlace($tpn(courant),$i,xy,y)\"\/> 
         <deltaLabel deltax=\"$tabPlace($tpn(courant),$i,label,dx)\" deltay=\"$tabPlace($tpn(courant),$i,label,dy)\"\/> 
      <\/graphics> 
      <scheduling gamma=\"$tabPlace($tpn(courant),$i,processeur)\" omega=\"$tabPlace($tpn(courant),$i,priorite)\"\/> 
  <\/place> \n" 
 
		} 
	    } 
 
	    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} { 
		if {$tabTransition($tpn(courant),$i,statut)==$ok} { 
		    if {$tabTransition($tpn(courant),$i,dmax)==$infini} { 
			set lft "inf" 
		    } else { 
			set lft $tabTransition($tpn(courant),$i,dmax) 
		    } 
		    if {$tabTransition($tpn(courant),$i,minparam)== "" && $tabTransition($tpn(courant),$i,maxparam)== ""} { 
			set params "" 
		    } elseif {$tabTransition($tpn(courant),$i,minparam)!= "" && $tabTransition($tpn(courant),$i,maxparam)!= ""} { 
			set params " eft_param=\"$tabTransition($tpn(courant),$i,minparam)\" lft_param=\"$tabTransition($tpn(courant),$i,maxparam)\"" 
		    } elseif {$tabTransition($tpn(courant),$i,minparam)!= ""} { 
			set params " eft_param=\"$tabTransition($tpn(courant),$i,minparam)\"" 
		    } elseif {$tabTransition($tpn(courant),$i,maxparam)!= ""} { 
			set params " lft_param=\"$tabTransition($tpn(courant),$i,maxparam)\"" 
		    } 
		    puts $File "  <transition id=\"$i\" identifier=\"$tabTransition($tpn(courant),$i,id)\" label=\"$tabTransition($tpn(courant),$i,label,nom)\" \
eft=\"$tabTransition($tpn(courant),$i,dmin)\" eftIncl=\"$tabTransition($tpn(courant),$i,eftIncl)\" lft=\"$lft\" lftIncl=\"$tabTransition($tpn(courant),$i,lftIncl)\" $params speed=\"$tabTransition($tpn(courant),$i,speed)\" priority=\"$tabTransition($tpn(courant),$i,priority)\" cost=\"$tabTransition($tpn(courant),$i,cost)\" unctrl=\"$tabTransition($tpn(courant),$i,unctrl)\" obs=\"$tabTransition($tpn(courant),$i,obs)\"  guard=\"[remplacerPartoutInfSupEq $tabTransition($tpn(courant),$i,guard)]\"> 
     <graphics color=\"$tabTransition($tpn(courant),$i,color)\"> 
        <position x=\"$tabTransition($tpn(courant),$i,xy,x)\" y=\"$tabTransition($tpn(courant),$i,xy,y)\"\/> 
        <deltaLabel deltax=\"$tabTransition($tpn(courant),$i,label,dx)\" deltay=\"$tabTransition($tpn(courant),$i,label,dy)\"\/> 
        <deltaGuard deltax=\"$tabTransition($tpn(courant),$i,guard,dx)\" deltay=\"$tabTransition($tpn(courant),$i,guard,dy)\"\/> 
        <deltaUpdate deltax=\"$tabTransition($tpn(courant),$i,update,dx)\" deltay=\"$tabTransition($tpn(courant),$i,update,dy)\"\/> 
        <deltaSpeed deltax=\"$tabTransition($tpn(courant),$i,speed,dx)\" deltay=\"$tabTransition($tpn(courant),$i,speed,dy)\"\/> 
        <deltaCost deltax=\"$tabTransition($tpn(courant),$i,cost,dx)\" deltay=\"$tabTransition($tpn(courant),$i,cost,dy)\"\/> 
     <\/graphics> 
     <update><!\[CDATA\[$tabTransition($tpn(courant),$i,update)\]\]><\/update> 
  <\/transition> \n" 
		} 
	    } 
 
	    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} { 
		if {$tabTransition($tpn(courant),$i,statut)==$ok} { 
		    for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} { 
# j'enleve dans le if qui suit : ||(($tabTransition($tpn(courant),$i,PorgType,$j)==4)&&($allowedArc(timedInhibitor)==0))
	               if {!((($tabTransition($tpn(courant),$i,PorgType,$j)==1)&&($allowedArc(reset)==0))||(($tabTransition($tpn(courant),$i,PorgType,$j)==2)&&($allowedArc(read)==0))||(($tabTransition($tpn(courant),$i,PorgType,$j)==3)&&($allowedArc(logicInhibitor)==0)))} {
			   puts $File "  <arc place=\"$tabTransition($tpn(courant),$i,Porg,$j)\" transition=\"$i\" type=\"[typeArc $i $j]\" weight=\"$tabTransition($tpn(courant),$i,PorgWeight,$j)\" tokenColor=\"$tabTransition($tpn(courant),$i,PorgTokenColor,$j)\"  inhibitingCondition=\"[remplacerPartoutInfSupEq $tabTransition($tpn(courant),$i,PorgInhibitingCondition,$j)]\"> 
    <nail xnail=\"$tabTransition($tpn(courant),$i,PorgNailx,$j)\" ynail=\"$tabTransition($tpn(courant),$i,PorgNaily,$j)\"\/> 
    <graphics  color=\"$tabTransition($tpn(courant),$i,PorgColor,$j)\"> 
     <\/graphics> 
  <\/arc> \n \n" 
		       }
		    } 
		    for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} { 
			puts $File "  <arc place=\"$tabTransition($tpn(courant),$i,Pdes,$j)\" transition=\"$i\" type=\"TransitionPlace\" weight=\"$tabTransition($tpn(courant),$i,PdesWeight,$j)\" tokenColor=\"$tabTransition($tpn(courant),$i,PdesTokenColor,$j)\"> 
     <nail xnail=\"$tabTransition($tpn(courant),$i,PdesNailx,$j)\" ynail=\"$tabTransition($tpn(courant),$i,PdesNaily,$j)\"\/> 
     <graphics  color=\"$tabTransition($tpn(courant),$i,PdesColor,$j)\"> 
     <\/graphics> 
  <\/arc> \n" 
		    } 
		} 
	    } 
 
	    if {[string length $tabConstraint($tpn(courant),0)] > 0} { 
		puts $File "  <misc>" 
		for {set i 0} {$i<$nbConstraints($tpn(courant))}  {incr i} { 
			if {[string length $tabConstraint($tpn(courant),$i)] > 0} { 
				set firstLow [string first "<" $tabConstraint($tpn(courant),$i) 0] 
				set firstHigh [string first ">" $tabConstraint($tpn(courant),$i) 0] 
				set firstEq [string first "=" $tabConstraint($tpn(courant),$i) 0] 
				set firstEqual [string first "==" $tabConstraint($tpn(courant),$i) 0] 
				set left $tabConstraint($tpn(courant),$i) 
				set right $tabConstraint($tpn(courant),$i) 
 
				if {$firstLow > 0} { 
					set left [string replace $left $firstLow end] 
					if {$firstEq > 0} {set op "LowerOrEqual"} else {set op "Lower"} 
					set right [string replace $right 0 [max $firstLow $firstEq]] 
				} elseif {$firstHigh > 0} { 
					set left [string replace $left $firstHigh end] 
					if {$firstEq > 0} {set op "GreaterOrEqual"} else {set op "Greater"} 
					set right [string replace $right 0 [max $firstHigh $firstEq]] 
				} elseif {$firstEqual > 0} { 
				    set left [string replace $left $firstEqual end] 
					set op "Equal" 
					set right [string replace $right 0  [expr $firstEqual+1]] 
				} 
				puts $File "     <constraint left=\"$left\" op=\"$op\" right=\"$right\"\/>" 
			} 
		} 
	        puts $File "  <\/misc>\n" 
	   } 
 

        puts $File "  <timedCost>$timedCost($tpn(courant))<\/timedCost>\n"

        puts $File "  <nbTokenColor>$nbTokenColor($tpn(courant))<\/nbTokenColor>\n"

	puts $File "  <declaration><!\[CDATA\[[retirerSupSupInfInf $declaration($tpn(courant))]\]\]><\/declaration>\n"

#	puts $File "  <initialization><!\[CDATA\[[retirerSupSupInfInf $initialization($tpn(courant))]\]\]><\/initialization>\n" 

	set nbSlave 0


	if {$esclave==0} {
	    for {set i 1}  {$i<=$projet($tpn(onglet),nbInput)} {incr i} { 
		if {$projet($tpn(onglet),input,$i,status)!="deleted"} {
		    set nbSlave [expr $nbSlave+1]
		}
	    }
	    puts $File "  <project nbinput=\"$nbSlave\" openinput=\"$projet($tpn(onglet),nbOpen)\" nbinclude=\"$projet($tpn(onglet),nbInclude)\" >"
	    set idSlave 1
	    for {set i 1} {$i <= $projet($tpn(onglet),nbInput)} {incr i} { 
		if {$projet($tpn(onglet),input,$i,status)!="deleted"} {
		    puts $File "      <input id=\"$idSlave\"  file=\"$projet($tpn(onglet),input,$i,file)\"  status=\"$projet($tpn(onglet),input,$i,status)\"\/>"
		    set idSlave [expr $idSlave+1]
		}
	    }
	} else {
	    puts $File "  <project nbinput=\"0\" openinput=\"0\" nbinclude=\"$projet($tpn(onglet),nbInclude)\" >"
	}

	for {set i 1} {$i <= $projet($tpn(onglet),nbInclude)} {incr i} { 
		puts $File "     <include id=\"$i\" file=\"$projet($tpn(onglet),include,$i,file)\"\/> "
	}
	puts $File " <\/project>\n"


# Synchronization-----------
#      puts $File "  <synchronization listSynch=\"$synchronized\"> \n <\/synchronization> \n" 
	     
# Preferences------------- 
     puts $File "  <preferences> " 
	  set colorPlace ""   
	  set colorTransition ""   
	  set colorArc ""   
      for {set i 0} {$i <= 5} {incr i} { 
	    set colorPlace "$colorPlace c$i=\"$tabColor(Place,$i)\" " 
	    set colorTransition "$colorTransition c$i=\"$tabColor(Transition,$i)\" " 
	    set colorArc "$colorArc c$i=\"$tabColor(Arc,$i)\" " 
      }  
 
     puts $File "      <colorPlace $colorPlace\/> \n " 
     puts $File "      <colorTransition $colorTransition\/> \n " 
     puts $File "      <colorArc $colorArc\/> \n " 
     puts $File "  <\/preferences> \n <\/TPN> \n"
     puts $File "  </romeo>" 
     close $File 
     affiche [mc "done"] 
     set modif($tpn(courant)) 0 
     update idletasks
     } 
} 
 
proc typeArc {indiceT indiceIP} { 
    global tabTransition 
    global tpn tabUnDo

 
	return [nomTypeArc $tabTransition($tpn(courant),$indiceT,PorgType,$indiceIP)]     
}   
 
proc nomTypeArc {numType} { 
    if {$numType==0} {  
	  return "PlaceTransition" 
    } elseif {$numType==1} {  
	  return "flush" 
    } elseif {$numType==2} {  
	  return "read" 
    } elseif {$numType==3} {  
	  return "logicalInhibitor" 
    } else { return "timedInhibitor"} 
}     
#++++++++++++++++++++++++++++++++++++++++++++++ 
 
 
#++++++++++++Verif nbPlace amont /proc(P)>0 est <2 ++++++ 
 
proc verifSem {avecAffichage} { 
    global tabPlace 
    global tabTransition 
    global nbProcesseur 
    global tpn tabUnDo 
    global fin 
    global ok 
    global francais 
 
    set erreurSemantique "" 
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin} {incr i} { 
        set amontOrdo 0 
        if {$tabTransition($tpn(courant),$i,statut)==$ok} { 
            for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0} {incr j} { 
                if {($tabPlace($tpn(courant),$tabTransition($tpn(courant),$i,Porg,$j),processeur)>0)&&($tabTransition($tpn(courant),$i,PorgType,$j)==0)} {incr amontOrdo} 
            } 
            if {$amontOrdo>1} { 
                if {$francais} { 
                    set erreurSemantique "$erreurSemantique \n               * Transition \" $tabTransition($tpn(courant),$i,id) \"  :  $amontOrdo arcs Pi->$tabTransition($tpn(courant),$i,id) avec proc(Pi)>0" 
                } else {     
                    set erreurSemantique "$erreurSemantique \n               * Transition \" $tabTransition($tpn(courant),$i,id) \"  :  $amontOrdo arcs Pi->$tabTransition($tpn(courant),$i,id) such that proc(Pi)>0 " 
                } 
            } 
        } 
    } 
    if {$erreurSemantique !=""} { 
	    affiche "\n > Semantic Error : $erreurSemantique" 
	    if {$avecAffichage==1} { 
	    set button [tk_messageBox -icon error -message [format [mc "Semantic error:  \n \n %s "] $erreurSemantique]] 
	} 
	return 0 
    } else { return 1 } 
} 
 
 
 
#+++++++++++++++++++++AFFICHAGE DANS LA FENETRE DE RESULTAT DE ROMEO +++++++++++++++++++++ 
 
proc affiche {texte} { 
    .romeo.global.out.texte insert end $texte 
    .romeo.global.out.texte yview moveto 1 
     update idletasks
 
}  
 
proc afficheBleu {texte} { 
    .romeo.global.out.texte tag configure bleu -foreground blue 
    .romeo.global.out.texte insert end $texte bleu 
    .romeo.global.out.texte yview moveto 1 
     update idletasks
}  
  
proc afficheMarron {texte} { 
    .romeo.global.out.texte tag configure marron -foreground brown 
    .romeo.global.out.texte insert end $texte marron 
    .romeo.global.out.texte yview moveto 1 
     update idletasks
}  

proc afficheRouge {texte} { 
    .romeo.global.out.texte tag configure rouge -foreground red 
    .romeo.global.out.texte insert end $texte rouge 
    .romeo.global.out.texte yview moveto 1 
     update idletasks
}  
 
#+++++++++++++++++++++AFFICHAGE GPN.LOG +++++++++++++++++++++ 
 
 
proc afficheGpnLog {lepid fichier} { 
    global plateforme 
 
    if {![string compare $plateforme "Darwin"]} { 
 
	if { [catch {open $fichier r} fid] } { 
	    affiche [format [mc "Unable to open %s"] $fichier] 
	} else { 
	    set File [open $fichier r] 
	    fileevent $File readable [afficheChannel $lepid 0 $File] 
	} 
    } else { 
	afficheBackGround $lepid "" 
    } 
} 
 
proc afficheBackGround {lepid lachaine} { 
    global plateforme 
 
    affiche "\n        $lepid >      " 
    affiche [format [mc "-Process %d will continue in background"] $lepid] 
 
    if {$lachaine != ""} { 
        affiche "\n        $lepid >      " 
        affiche [mc "-The file "]  
        afficheBleu $lachaine 
        affiche [mc " will be generated"] 
    } 
    if {[string compare $plateforme "windows"]} { 
	affiche "\n        $lepid >      "  
	affiche [mc "-Use ps (or top) command to display information about processes."] 
	#     affiche "\n        $lepid >      " 
	#     affiche [format [mc "-Use kill -9 %d to terminate the process."] $lepid] 
    } else { 
	affiche "\n        $lepid >      " 
	affiche [mc "-Use alt/ctrl/sup to manage the process."] 
    } 
} 
 
proc attendreAffiche  {lepid temps File} { 
 
    incr temps 
    if {($temps/10.0)==($temps/10)} { 
	  affiche "\n        $lepid >      " 
	  affiche [format [mc "...running time : %d  s ..."] [expr $temps*2]] 
    } 
    if {$temps<100} { 
	  after cancel afficheChannel $lepid $temps $File 
	  if {[catch [after 2000 afficheChannel $lepid $temps $File]]} {} 
    } else { 
	   affiche "\n        $lepid >      " 
	   affiche [mc "Running time display aborted"] 
	   afficheBackGround $lepid "" 
    } 
} 
 
proc afficheChannel {lepid temps File} { 
    set endOfFil 0 
    set nlig [tell $File]  
    set ligne [gets $File]  
    seek $File $nlig start 
    while {([eof $File] <1) && ([fblocked $File] <1)} { 
	set ligne [gets $File] 
	if {![string compare [nextExpression $ligne " "] "Total"]} { 
	    set endOfFil 1 
	} 
	if {[string compare $ligne ""]} { 
	    affiche "\n        $lepid >      $ligne " 
            update idletasks
	} 
    }  
    set nlig [tell $File]     
    if {$endOfFil==0} { 
	fileevent $File readable [attendreAffiche $lepid $temps $File] 
    } else { 
	close $File 
    } 
} 
 
 
#+++++++++++++++++++++FIN AFFICHAGE GPN.LOG +++++++++++++++++++++ 
 
 
proc tailleX {} { 
    global tabPlace 
    global tabTransition 
    global tpn tabUnDo
    global fin 
    global ok 
    global maxX 
 
    set lplX 0 
 
    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} { 
        if {$tabPlace($tpn(courant),$i,statut)==$ok} { 
	    if { $tabPlace($tpn(courant),$i,xy,x) > $lplX } { 
		set lplX  $tabPlace($tpn(courant),$i,xy,x) 
	    } 
	    if { ($tabPlace($tpn(courant),$i,xy,x)+$tabPlace($tpn(courant),$i,label,dx)) > $lplX } { 
		set lplX  [expr $tabPlace($tpn(courant),$i,xy,x)+$tabPlace($tpn(courant),$i,label,dx)] 
	    } 
        } 
    } 
 
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} { 
	if {$tabTransition($tpn(courant),$i,statut)==$ok} { 
	    if { $tabTransition($tpn(courant),$i,xy,x) > $lplX } { 
		set lplX $tabTransition($tpn(courant),$i,xy,x) 
	    } 
	    if { ($tabTransition($tpn(courant),$i,xy,x)+$tabTransition($tpn(courant),$i,label,dx)) > $lplX } { 
		set lplX [expr $tabTransition($tpn(courant),$i,xy,x)+$tabTransition($tpn(courant),$i,label,dx)] 
	    } 
	    for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} { 
		if {$tabTransition($tpn(courant),$i,PorgNailx,$j)>$lplX } { 
		    set lplX $tabTransition($tpn(courant),$i,PorgNailx,$j) 
		} 
	    } 
	    for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} { 
		if {$tabTransition($tpn(courant),$i,PdesNailx,$j)>$lplX } { 
		    set lplX $tabTransition($tpn(courant),$i,PdesNailx,$j) 
		} 
	    } 
	} 
    } 
 
    # set lplX [expr 50*($lplX+20)/$maxX] 
    return $lplX 
 
} 
 
 
proc tailleY {} { 
    global tabPlace 
    global tabTransition 
    global tpn tabUnDo
    global fin 
    global ok 
    global maxY 
 
    set lplY 0 
 
    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} { 
        if {$tabPlace($tpn(courant),$i,statut)==$ok} { 
	    if {$tabPlace($tpn(courant),$i,xy,y) > $lplY} { 
		set lplY  $tabPlace($tpn(courant),$i,xy,y) 
	    } 
	    if { ($tabPlace($tpn(courant),$i,xy,y)+$tabPlace($tpn(courant),$i,label,dy)) > $lplY } { 
		set lplY  [expr $tabPlace($tpn(courant),$i,xy,y)+$tabPlace($tpn(courant),$i,label,dy)] 
	    } 
        } 
    } 
 
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} { 
        if {$tabTransition($tpn(courant),$i,statut)==$ok} { 
            if {$tabTransition($tpn(courant),$i,xy,y) > $lplY} { 
		set lplY $tabTransition($tpn(courant),$i,xy,y) 
            } 
 	    if { ($tabTransition($tpn(courant),$i,xy,y)+$tabTransition($tpn(courant),$i,label,dy)) > $lplY } { 
		set lplY [expr $tabTransition($tpn(courant),$i,xy,y)+$tabTransition($tpn(courant),$i,label,dy)] 
            } 
	    for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} { 
		if {$tabTransition($tpn(courant),$i,PorgNaily,$j)>$lplY } { 
		    set lplY $tabTransition($tpn(courant),$i,PorgNaily,$j) 
		} 
	    } 
	    for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} { 
		if {$tabTransition($tpn(courant),$i,PdesNaily,$j)>$lplY } { 
		    set lplY $tabTransition($tpn(courant),$i,PdesNaily,$j) 
		} 
	    } 
	} 
    } 
    #set lplY [expr 33*($lplY+20)/$maxY] 
    return $lplY 
} 
 
 
 
proc sansEspace {phrase} { 
    set x 0 
    while {[string index $phrase $x] == " "} {incr x} 
    set phrase [string range $phrase $x [string length $phrase] ] 
 
    set espace [string first " " $phrase] 
    while {$espace > 0} { 
	set concatGauche [string range $phrase 0 [expr $espace -1]] 
	set concatDroite [string range $phrase [expr $espace + 1] [string length $phrase] ] 
 
	set phrase "$concatGauche$concatDroite" 
	set espace [string first " " $phrase] 
    } 
    return $phrase 
} 
 

proc retirerListeCar {phrase listeCar} { 
  for {set i 0} {$i<[llength $listeCar]} {incr i} {
     set car  [lindex $listeCar $i]
     set x 0 
     while {[string index $phrase $x] == $car} {incr x} 
     set phrase [string range $phrase $x [string length $phrase] ] 
 
     set indice [string first $car $phrase] 
     while {$indice > 0} { 
	set concatGauche [string range $phrase 0 [expr $indice -1]] 
	set concatDroite [string range $phrase [expr $indice + 1] [string length $phrase] ] 
 
	set phrase "$concatGauche$concatDroite" 
 	set indice [string first $car $phrase] 
     } 
  }
  return $phrase 
} 
 

 
proc slach {phrase} { 
    set antislach "\\" 
    set espace [string first "/" $phrase] 
    while {$espace > 0} { 
	set concatGauche [string range $phrase 0 [expr $espace -1]] 
	set concatDroite [string range $phrase [expr $espace + 1] [string length $phrase] ] 
 
	set phrase "$concatGauche$antislach$concatDroite" 
	set espace [string first "/" $phrase] 
    } 
    return $phrase 
} 
 
proc parcourir {repertoire} { 
 
    set repertoireChoisi [tk_chooseDirectory -initialdir $repertoire \
			      -title [mc "Choose a directory"]] 
    if [string compare $repertoireChoisi ""] { 
        return $repertoireChoisi 
    } else { 
        return $repertoire 
    } 
} 
 
proc repertoire {nomFichier} { 
 
    set last [string last "/" $nomFichier] 
 
    if {$last>=0} {set resultat [string range $nomFichier 0 [expr $last -1]] 
    } else {set resultat "./"} 
    return $resultat 
} 
 
proc existCarDansMot {mot separateur} {
    set firstPosition [string first $separateur $mot]
    if {$firstPosition >=0} { 
	return 1
      } else {
	  return 0
      }
}

proc nomSeul {nomFichier} { 
 
    set last [string last "/" $nomFichier] 
 
    if {$last>=0} {set resultat [string range $nomFichier [expr $last +1] [string length $nomFichier] ] 
    } else {set resultat $nomFichier} 
    return $resultat 
}


proc nomRelatif {nomComplet repertoire} { 

    if {[string first $repertoire $nomComplet] < 0 } {
	return ""
    } else {
	return [string range  $nomComplet [string length $repertoire] [string length $nomComplet]]
    }
 }


proc sansXml {nomFichier} { 

    set last [string first ".xml" "$nomFichier"] 

    if {$last>=0} {
     return [string range "$nomFichier" 0 [expr $last -1]] 
    } else {
      return $nomFichier
    }

}

# -----------------------------------------------------EXPORT POUR TOUTES LES VALEURS DES PARAMETRES------------------------------
proc genererValParamXml {} { 
    global tabPlace tabTransition tabConstraint 
    global nbProcesseur tpn scheduling 
    global fin ok destroy nomRdP
    global modif 
    global infini 
    global tabColor 
    global nbConstraints 
    global tpn tabUnDo
    global allowedArc
    global synchronized
 
#puts $nomRdP($tpn(onglet))
 
    set nomDeBase [sansXml $nomRdP($tpn(onglet))]
    set extScript "-Script"
    set nomScript "$nomDeBase$extScript" 
    set lescript [open $nomScript w] 

 	    set declarPlaces ""
            set fictifTPN -1

  	    set nbConstraints($fictifTPN) $nbConstraints($tpn(courant))
  	    for {set i 0} {$i<$nbConstraints($tpn(courant))}  {incr i} { 
		set tabConstraint($fictifTPN,$i) $tabConstraint($tpn(courant),$i) 
	    }

	    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} { 
		if {$tabPlace($tpn(courant),$i,statut)==$ok} { 
		    if {$tabPlace($tpn(courant),$i,dmax)==$infini} { 
			set lft "inf" 
		    } else { 
			set lft $tabPlace($tpn(courant),$i,dmax) 
		    } 
	    	    set declarPlaces "$declarPlaces \n  <place id=\"$i\" identifier=\"$tabPlace($tpn(courant),$i,id)\" label=\"$tabPlace($tpn(courant),$i,label,nom)\" initialMarking=\"$tabPlace($tpn(courant),$i,jeton)\"> 
      <graphics color=\"$tabPlace($tpn(courant),$i,color)\"> 
         <position x=\"$tabPlace($tpn(courant),$i,xy,x)\" y=\"$tabPlace($tpn(courant),$i,xy,y)\"\/> 
         <deltaLabel deltax=\"$tabPlace($tpn(courant),$i,label,dx)\" deltay=\"$tabPlace($tpn(courant),$i,label,dy)\"\/> 
      <\/graphics> 
      <scheduling gamma=\"$tabPlace($tpn(courant),$i,processeur)\" omega=\"$tabPlace($tpn(courant),$i,priorite)\"\/> 
  <\/place> \n" 
 
		} 
		set tabPlace($fictifTPN,$i,statut) $tabPlace($tpn(courant),$i,statut)
		set tabPlace($fictifTPN,$i,jeton) $tabPlace($tpn(courant),$i,jeton)
		set tabPlace($fictifTPN,$i,label,nom) $tabPlace($tpn(courant),$i,label,nom)
		set tabPlace($fictifTPN,$i,id) $tabPlace($tpn(courant),$i,id)
	    } 
        # STATUT = $fin
	set tabPlace($fictifTPN,$i,statut) $tabPlace($tpn(courant),$i,statut)   

    set declarArcs ""
	    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} { 

		set tabTransition($fictifTPN,$i,statut) $tabTransition($tpn(courant),$i,statut)

		if {$tabTransition($tpn(courant),$i,statut)==$ok} { 
		    for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} { 
# j'enleve dans le if qui suit : ||(($tabTransition($tpn(courant),$i,PorgType,$j)==4)&&($allowedArc(timedInhibitor)==0))
	               if {!((($tabTransition($tpn(courant),$i,PorgType,$j)==1)&&($allowedArc(reset)==0))||(($tabTransition($tpn(courant),$i,PorgType,$j)==2)&&($allowedArc(read)==0))||(($tabTransition($tpn(courant),$i,PorgType,$j)==3)&&($allowedArc(logicInhibitor)==0)))} {
			   set declarArcs "$declarArcs  <arc place=\"$tabTransition($tpn(courant),$i,Porg,$j)\" transition=\"$i\" type=\"[typeArc $i $j]\" weight=\"$tabTransition($tpn(courant),$i,PorgWeight,$j)\" tokenColor=\"$tabTransition($tpn(courant),$i,PorgTokenColor,$j)\" inhibitingCondition=\"[remplacerPartoutInfSupEq $tabTransition($tpn(courant),$i,PorgInhibitingCondition,$j)]\"> 
    <nail xnail=\"$tabTransition($tpn(courant),$i,PorgNailx,$j)\" ynail=\"$tabTransition($tpn(courant),$i,PorgNaily,$j)\"\/> 
    <graphics  color=\"$tabTransition($tpn(courant),$i,PorgColor,$j)\"> 
     <\/graphics> 
  <\/arc> \n \n" 
		       }		
		       set tabTransition($fictifTPN,$i,Porg,$j) $tabTransition($tpn(courant),$i,Porg,$j)
		       set tabTransition($fictifTPN,$i,PorgType,$j) $tabTransition($tpn(courant),$i,PorgType,$j)
		       set tabTransition($fictifTPN,$i,PorgWeight,$j) $tabTransition($tpn(courant),$i,PorgWeight,$j)
		       set tabTransition($fictifTPN,$i,PorgTokenColor,$j) $tabTransition($tpn(courant),$i,PorgTokenColor,$j)
		       set tabTransition($fictifTPN,$i,PorgInhibitingCondition,$j) $tabTransition($tpn(courant),$i,PorgInhibitingCondition,$j)
		    } 
		    # dernier Porg,j = 0
		    set tabTransition($fictifTPN,$i,Porg,$j) $tabTransition($tpn(courant),$i,Porg,$j)
		    
		    for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} { 

			set declarArcs "$declarArcs  <arc place=\"$tabTransition($tpn(courant),$i,Pdes,$j)\" transition=\"$i\" type=\"TransitionPlace\" weight=\"$tabTransition($tpn(courant),$i,PdesWeight,$j)\" tokenColor=\"$tabTransition($tpn(courant),$i,PdesTokenColor,$j)\"> 
     <nail xnail=\"$tabTransition($tpn(courant),$i,PdesNailx,$j)\" ynail=\"$tabTransition($tpn(courant),$i,PdesNaily,$j)\"\/> 
     <graphics  color=\"$tabTransition($tpn(courant),$i,PdesColor,$j)\"> 
     <\/graphics> 
  <\/arc> \n" 
		       set tabTransition($fictifTPN,$i,Pdes,$j) $tabTransition($tpn(courant),$i,Pdes,$j)
		       set tabTransition($fictifTPN,$i,PdesWeight,$j) $tabTransition($tpn(courant),$i,PdesWeight,$j)
		       set tabTransition($fictifTPN,$i,PdesTokenColor,$j) $tabTransition($tpn(courant),$i,PdesTokenColor,$j)

		    } 
		    # dernier Pdes,j = 0
		    set tabTransition($fictifTPN,$i,Pdes,$j) $tabTransition($tpn(courant),$i,Pdes,$j)

		} 
	    } 
           # statut = fin
           set tabTransition($fictifTPN,$i,statut) $tabTransition($tpn(courant),$i,statut)


set maxi 10
     for {set a 0} {$a<=$maxi}  {incr a} { 
       for {set b 1} {$b<=$maxi}  {incr b} { 
#         for {set c 18} {$c<=18}  {incr c} { 
#	     for {set d 100} {$d<=100}  {incr d} { 
	     set borneOk 1
# puts "$a $b"
	     for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} { 
		 if {($borneOk)&&($tabTransition($tpn(courant),$i,statut)==$ok)} { 
	
		     set boundMin $tabTransition($tpn(courant),$i,minparam)
		     set boundMax $tabTransition($tpn(courant),$i,maxparam)
		     if {$boundMin==""} {set boundMin 0}
		     if {$boundMax==""} {set boundMax $infini}

		     set boundMin [string map {a $a} $boundMin]
		     set boundMin [string map {b $b} $boundMin]
		     set boundMin [string map {c $c} $boundMin]
		     set boundMin [string map {d $d} $boundMin]
		     set boundMax [string map {a $a} $boundMax]
		     set boundMax [string map {b $b} $boundMax]
		     set boundMax [string map {c $c} $boundMax]
		     set boundMax [string map {d $d} $boundMax]
			    
#puts "$boundMin $boundMax"

	             set theBoundMin($i) [expr $boundMin]
                     set theBoundMax($i) [expr $boundMax]

		     if {$theBoundMin($i)>$theBoundMax($i)} { set borneOk 0} 
		     if {$theBoundMax($i)==$infini} { set theBoundMax($i) "inf"} 
#puts "hop$i $tabTransition($tpn(courant),$i,label,nom) $theBoundMin($i) $theBoundMax($i)"

		 }
	     }
	     if {$borneOk} {
#		 set fichier "$nomDeBase-A$a\-B$b\-C$c\-D$d.xml"
		 set fichier "$nomDeBase-A$a\-B$b.xml"
		 set fichierCTS "$nomDeBase-A$a\-B$b.cts"
		 puts $fichier
# LE SCRIPT POUR ITS
#puts $lescript "time .\/its-reach -t ROMEO -i $fichier -reachable \'P_11PTask1>1||P_6PTask2>1||P_7PTask3>1\' \n"
# LE SCRIPT POUR ROMEO
#puts $lescript "time .\/bin\/mercutio-tctl -t  --max-tokens=50000 --max-nodes=-1   -f  train3-prop-phi2.tctl $fichier \n"
# LE SCRIPT POUR CTS
puts $lescript "time .\/romeo-cli $fichier \n"
		 affiche " \n" 
		 affiche [mc "-Export net as "] 
		 afficheBleu $fichier 
		 affiche " ..." 

		 if { [catch {open $fichier w} fid] } { 
		     affiche [format [mc "Unable to open %s"] $fichier] 
		 } else {
		  set File [open $fichier w] 
		  puts $File "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>" 
		  puts $File "<TPN name=\"$fichier\">" 
 
		  puts $File "$declarPlaces" 
		 
	     
		  for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} { 
		     if {$tabTransition($tpn(courant),$i,statut)==$ok} { 
			 puts $File "  <transition id=\"$i\" label=\"$tabTransition($tpn(courant),$i,label,nom)\" \
eft=\"$theBoundMin($i)\" lft=\"$theBoundMax($i)\" unctrl=\"$tabTransition($tpn(courant),$i,unctrl) obs=\"$tabTransition($tpn(courant),$i,obs)\"> 
     <graphics color=\"$tabTransition($tpn(courant),$i,color)\"> 
        <position x=\"$tabTransition($tpn(courant),$i,xy,x)\" y=\"$tabTransition($tpn(courant),$i,xy,y)\"\/> 
        <deltaLabel deltax=\"$tabTransition($tpn(courant),$i,label,dx)\" deltay=\"$tabTransition($tpn(courant),$i,label,dy)\"\/> 
     <\/graphics> 
  <\/transition> \n" 
# le nom, on aurait pu le mettre au dessus en meme temps que le statut les pdes et les porg
			 set tabTransition($fictifTPN,$i,label,nom) $tabTransition($tpn(courant),$i,label,nom)
			 set tabTransition($fictifTPN,$i,minparam) $theBoundMin($i)
			 set tabTransition($fictifTPN,$i,dmin) $theBoundMin($i)
			 set tabTransition($fictifTPN,$i,maxparam) $theBoundMax($i)
			 set tabTransition($fictifTPN,$i,dmax) $theBoundMax($i)

		     } 
		 } 

 		  puts $File "$declarArcs" 
		  puts $File "\n <\/TPN>" 


		 close $File 
		 set nomRdP($fictifTPN) $fichier
		 export2CTS $fictifTPN $fichierCTS "" 0
		 affiche [mc "done"] 
		 update idletasks
		 }
	     }
#	 }
#       }
     }
     }
    close $lescript	
} 
 

proc modifTPN {leTPN} { 
    global modif 
    global tpn tabUnDo nomRdP select
    global tabPlace tabTransition tabConstraint timedCost nbTokenColor
    global declaration initialization
    global nbProcesseur scheduling 
    global fin ok 
    global infini 
    global nbConstraints tabConstraint
 
    set stopModifTPN 0
    if {($modif(freeze)==0)&&($stopModifTPN==0)} {

    set tpn(courant) $leTPN

# En fait on considere toujours leTPN = tpn(courant) - ce n'est peut etre pas malin - il vaudrait mieux prendre  tpn(onglet)

    set modif($leTPN) 1   

    set tpn(slave) [retrouverMasterSlave]


    set masterSlave [expr $tpn(onglet)*100+$tpn(slave)]
    if {$tabUnDo($masterSlave,courant) == 99} {
	set tabUnDo($masterSlave,courant) 0
    } else {
	set tabUnDo($masterSlave,courant) [expr $tabUnDo($masterSlave,courant)+1]
    }

    if {$tabUnDo($masterSlave,taille) < 100} {
	set tabUnDo($masterSlave,taille) [expr $tabUnDo($masterSlave,taille)+1]
    }
    set futur [calculTPNCourant $tpn(slave)]


    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} { 
	set tabPlace($futur,$i,statut) $tabPlace($tpn(courant),$i,statut)
	set tabPlace($futur,$i,color)   $tabPlace($tpn(courant),$i,color) 
	set tabPlace($futur,$i,xy,x)  $tabPlace($tpn(courant),$i,xy,x) 
	set tabPlace($futur,$i,xy,y)  $tabPlace($tpn(courant),$i,xy,y) 
	set tabPlace($futur,$i,label,nom)  $tabPlace($tpn(courant),$i,label,nom) 
	set tabPlace($futur,$i,id)  $tabPlace($tpn(courant),$i,id) 
	set tabPlace($futur,$i,label,dx)  $tabPlace($tpn(courant),$i,label,dx) 
	set tabPlace($futur,$i,label,dy)  $tabPlace($tpn(courant),$i,label,dy) 
	set tabPlace($futur,$i,processeur)  $tabPlace($tpn(courant),$i,processeur)
	set tabPlace($futur,$i,priorite)  $tabPlace($tpn(courant),$i,priorite) 
	set tabPlace($futur,$i,jeton)  $tabPlace($tpn(courant),$i,jeton) 
	set tabPlace($futur,$i,dmin)  $tabPlace($tpn(courant),$i,dmin) 
	set tabPlace($futur,$i,dmax)  $tabPlace($tpn(courant),$i,dmax)
    } 
    set tabPlace($futur,$i,statut) $tabPlace($tpn(courant),$i,statut)

 
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} { 
	set tabTransition($futur,$i,statut) $tabTransition($tpn(courant),$i,statut) 
	set tabTransition($futur,$i,color) $tabTransition($tpn(courant),$i,color) 
	set tabTransition($futur,$i,xy,x)  $tabTransition($tpn(courant),$i,xy,x) 
	set tabTransition($futur,$i,xy,y)  $tabTransition($tpn(courant),$i,xy,y) 
	set tabTransition($futur,$i,label,nom) $tabTransition($tpn(courant),$i,label,nom) 
	set tabTransition($futur,$i,id) $tabTransition($tpn(courant),$i,id) 
	set tabTransition($futur,$i,label,dx) $tabTransition($tpn(courant),$i,label,dx) 
	set tabTransition($futur,$i,label,dy) $tabTransition($tpn(courant),$i,label,dy) 
	set tabTransition($futur,$i,guard,dx) $tabTransition($tpn(courant),$i,guard,dx) 
	set tabTransition($futur,$i,guard,dy) $tabTransition($tpn(courant),$i,guard,dy) 
	set tabTransition($futur,$i,update,dx) $tabTransition($tpn(courant),$i,update,dx)
	set tabTransition($futur,$i,update,dy) $tabTransition($tpn(courant),$i,update,dy)
	set tabTransition($futur,$i,speed,dx) $tabTransition($tpn(courant),$i,speed,dx) 
	set tabTransition($futur,$i,speed,dy) $tabTransition($tpn(courant),$i,speed,dy) 
	set tabTransition($futur,$i,speed)  $tabTransition($tpn(courant),$i,speed) 
	set tabTransition($futur,$i,priority)  $tabTransition($tpn(courant),$i,priority) 
	set tabTransition($futur,$i,cost,dx) $tabTransition($tpn(courant),$i,cost,dx) 
	set tabTransition($futur,$i,cost,dy) $tabTransition($tpn(courant),$i,cost,dy) 
	set tabTransition($futur,$i,cost) $tabTransition($tpn(courant),$i,cost) 
	set tabTransition($futur,$i,dmin) $tabTransition($tpn(courant),$i,dmin) 
	set tabTransition($futur,$i,dmax) $tabTransition($tpn(courant),$i,dmax) 
	set tabTransition($futur,$i,eftIncl) $tabTransition($tpn(courant),$i,eftIncl) 
	set tabTransition($futur,$i,lftIncl) $tabTransition($tpn(courant),$i,lftIncl) 
	set tabTransition($futur,$i,minparam) $tabTransition($tpn(courant),$i,minparam) 
	set tabTransition($futur,$i,maxparam) $tabTransition($tpn(courant),$i,maxparam) 
	set tabTransition($futur,$i,obs) $tabTransition($tpn(courant),$i,obs) 
	set tabTransition($futur,$i,unctrl) $tabTransition($tpn(courant),$i,unctrl) 
	set tabTransition($futur,$i,update) $tabTransition($tpn(courant),$i,update) 
	set tabTransition($futur,$i,guard) $tabTransition($tpn(courant),$i,guard) 
	set parikhVector($tpn(courant),$i) 0

	for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} { 
	    set tabTransition($futur,$i,Porg,$j)  $tabTransition($tpn(courant),$i,Porg,$j) 
	    set tabTransition($futur,$i,PorgNailx,$j)  $tabTransition($tpn(courant),$i,PorgNailx,$j) 
	    set tabTransition($futur,$i,PorgNaily,$j)  $tabTransition($tpn(courant),$i,PorgNaily,$j) 
	    set tabTransition($futur,$i,PorgWeight,$j) $tabTransition($tpn(courant),$i,PorgWeight,$j) 
	    set tabTransition($futur,$i,PorgInhibitingCondition,$j) $tabTransition($tpn(courant),$i,PorgInhibitingCondition,$j) 
	    set tabTransition($futur,$i,PorgType,$j)  $tabTransition($tpn(courant),$i,PorgType,$j) 
	    set tabTransition($futur,$i,PorgColor,$j) $tabTransition($tpn(courant),$i,PorgColor,$j)
	    set tabTransition($futur,$i,PorgTokenColor,$j) $tabTransition($tpn(courant),$i,PorgTokenColor,$j)
	}
	set tabTransition($futur,$i,Porg,$j)  $tabTransition($tpn(courant),$i,Porg,$j) 
	set tabTransition($futur,$i,PorgNailx,$j)  $tabTransition($tpn(courant),$i,PorgNailx,$j) 
	set tabTransition($futur,$i,PorgNaily,$j)  $tabTransition($tpn(courant),$i,PorgNaily,$j) 
	set tabTransition($futur,$i,PorgWeight,$j) $tabTransition($tpn(courant),$i,PorgWeight,$j) 
	set tabTransition($futur,$i,PorgInhibitingCondition,$j) $tabTransition($tpn(courant),$i,PorgInhibitingCondition,$j) 
	set tabTransition($futur,$i,PorgType,$j)  $tabTransition($tpn(courant),$i,PorgType,$j) 
	set tabTransition($futur,$i,PorgColor,$j) $tabTransition($tpn(courant),$i,PorgColor,$j)
	set tabTransition($futur,$i,PorgTokenColor,$j) $tabTransition($tpn(courant),$i,PorgTokenColor,$j)
	for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} { 
	    set tabTransition($futur,$i,Pdes,$j) $tabTransition($tpn(courant),$i,Pdes,$j) 
	    set tabTransition($futur,$i,PdesNailx,$j) $tabTransition($tpn(courant),$i,PdesNailx,$j) 
	    set tabTransition($futur,$i,PdesNaily,$j) $tabTransition($tpn(courant),$i,PdesNaily,$j) 
	    set tabTransition($futur,$i,PdesWeight,$j) $tabTransition($tpn(courant),$i,PdesWeight,$j) 
	    set tabTransition($futur,$i,PdesColor,$j) $tabTransition($tpn(courant),$i,PdesColor,$j) 
	    set tabTransition($futur,$i,PdesTokenColor,$j) $tabTransition($tpn(courant),$i,PdesTokenColor,$j) 
	}
	set tabTransition($futur,$i,Pdes,$j) $tabTransition($tpn(courant),$i,Pdes,$j) 
	set tabTransition($futur,$i,PdesNailx,$j) $tabTransition($tpn(courant),$i,PdesNailx,$j) 
	set tabTransition($futur,$i,PdesNaily,$j) $tabTransition($tpn(courant),$i,PdesNaily,$j) 
	set tabTransition($futur,$i,PdesWeight,$j) $tabTransition($tpn(courant),$i,PdesWeight,$j) 
	set tabTransition($futur,$i,PdesColor,$j) $tabTransition($tpn(courant),$i,PdesColor,$j) 
	set tabTransition($futur,$i,PdesTokenColor,$j) $tabTransition($tpn(courant),$i,PdesTokenColor,$j) 

    }
    set tabTransition($futur,$i,statut) $tabTransition($tpn(courant),$i,statut) 

    for {set i 0} {$i<$nbConstraints($tpn(courant))}  {incr i} { 
	set tabConstraint($futur,$i) $tabConstraint($tpn(courant),$i)
    }
    set nbConstraints($futur) $nbConstraints($tpn(courant)) 

    valideclarOnglet $tpn(onglet) $tpn(courant)
    set declaration($futur) $declaration($tpn(courant))

    valideIniOnglet $tpn(onglet) $tpn(courant)
    set initialization($futur) $initialization($tpn(courant))

    set timedCost($futur) $timedCost($tpn(courant))

    set nbTokenColor($futur) $nbTokenColor($tpn(courant))

    set nbProcesseur($futur) $nbProcesseur($tpn(courant))

    if {$select(tpn) ==  $tpn(courant)} { set select(tpn) $futur}
    set tpn(courant) $futur

    set modif($tpn(courant)) 1
}
}


proc unDoModif {w} {
    global modif nomRdP
    global tpn tabUnDo
    global tabPlace tabTransition tabConstraint timedCost nbTokenColor
    global declaration initialization
    global nbProcesseur scheduling 
    global fin ok 
    global infini select
 
#    if {[winfo exists .declaration$tpn(onglet)]} {
#	set lastDeclar [.declaration$leOnglet.text get get 1.0 end]
 #   }

  #  if {[winfo exists .initialization$leOnglet)]} {
#	set lastInit [.initialization$leOnglet.text get 1.0 {end -1c}]
 #   }

    set masterSlave [expr $tpn(onglet)*100+$tpn(slave)]
    if {$tabUnDo($masterSlave,taille) > 1} {
	set tabUnDo($masterSlave,taille) [expr $tabUnDo($masterSlave,taille)-1]
 
       set ancientpncourant [calculTPNCourant $tpn(slave)]

       if {$tabUnDo($masterSlave,courant) == 0} {
	   set tabUnDo($masterSlave,courant) 99
       } else {
	   set tabUnDo($masterSlave,courant) [expr $tabUnDo($masterSlave,courant)-1]
       }

       set tpn(courant) [calculTPNCourant $tpn(slave)]

#vider le tampon
	set select(vide) 1
	set select(listePlace) [list]
	set select(listeLabelPlace) [list]
	set select(listeTransition) [list]
	set select(listeLabelTransition) [list]
	set select(listeNoeud) [list]


	if {$declaration($tpn(courant))!=$declaration($ancientpncourant)} {
	    if {[winfo exists .declaration$tpn(onglet)]} {
		.declaration$tpn(onglet).text delete 1.0 end
#	   .declaration$tpn(onglet).text insert 1.0 "here is my text to insert"
		.declaration$tpn(onglet).text insert end $declaration($tpn(courant))
		raise .declaration$tpn(onglet)

	    } else {
		ouvrirDeclaration $tpn(onglet) [nomSeul $nomRdP($tpn(onglet))]
	    }
       }

	if {$initialization($tpn(courant))!=$initialization($ancientpncourant)} {
	    if {[winfo exists .initialization$tpn(onglet)]} {
		.initialization$tpn(onglet).text delete 1.0 end
		.initialization$tpn(onglet).text insert end $initialization($tpn(courant))
		raise .initialization$tpn(onglet)
	    } else { 
		ouvrirInitialization $tpn(onglet) [nomSeul $nomRdP($tpn(onglet))]
	    }
       }

	if {$tpn(slave)==0} { 	    
	    redessinerRdP $w.frame.c
	} else {
	    redessinerRdP $w.slave.slave$tpn(slave).dessin.c 
	}
   }
}
