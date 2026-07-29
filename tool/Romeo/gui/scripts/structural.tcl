package require math::linearalgebra
proc axpby_vect {a vect1 b  vect2 } {
    set result {}

    foreach c1 $vect1 c2 $vect2 {
        lappend result [expr $a*$c1+$b*$c2]
    }
    return $result
}





proc invariant {} {   
    global tabPlace tabTransition
    global fin ok 
    global nomRdP tpn projet
    global matricePre matricePost listeTransition vecteurM0



    set fenetreAnalyseStructurelle .fenetreStruc 
    catch {destroy $fenetreAnalyseStructurelle} 
    toplevel $fenetreAnalyseStructurelle 

    wm title $fenetreAnalyseStructurelle [mc "Romeo Structural Analysis"] 

    

    frame $fenetreAnalyseStructurelle.matrix
    pack $fenetreAnalyseStructurelle.matrix -side top -fill both
    button $fenetreAnalyseStructurelle.matrix.bouton -text [mc "Save Matrix"] -font menufont \
	-command "exporterMatrice"
    pack $fenetreAnalyseStructurelle.matrix.bouton  -side top

    frame $fenetreAnalyseStructurelle.resultat
    pack $fenetreAnalyseStructurelle.resultat -side top -fill both
    
    set fenetreAnalyseStruct $fenetreAnalyseStructurelle.resultat
    
    text $fenetreAnalyseStruct.text -yscrollcommand "$fenetreAnalyseStruct.scroll set" -setgrid true \
	-width 60 -height 40 -wrap word -bg white -font fontEditor
    scrollbar $fenetreAnalyseStruct.scroll -command "$fenetreAnalyseStruct.text yview" 
     
    pack $fenetreAnalyseStruct.scroll -side right -fill y 
     
    pack $fenetreAnalyseStruct.text -expand yes -fill both 
    $fenetreAnalyseStruct.text tag configure rouge -foreground red 
    $fenetreAnalyseStruct.text tag configure bleu -foreground blue 
    $fenetreAnalyseStruct.text tag configure surgris -background #a0b7ce 
    $fenetreAnalyseStruct.text tag configure souligne -underline on 
 
 
	#******************** en anglais****************** 
    $fenetreAnalyseStruct.text insert end "Petri net :   [nomSeul $nomRdP($tpn(onglet))] \n" 

    
    set letpn $tpn(courant)

    set resultat ""
    set listeTransition {}
    set listePlace {}
    set indiceT 0
    set indiceP 0
    set vecteurM0 {}
    set matriceCT {}
    set matricePreT {}
    set matricePostT {}
    set nbPlace 0
    set nbPlaceOk 0
    set nbTransition 0
    set nbTransitionOk 0
    set vectNull {}

    for {set i 1} {$tabPlace($letpn,$i,statut)!=$fin} {incr i} {
	set nbPlace [expr $nbPlace+1]
	set vectNull  [linsert $vectNull 0 0]
	if {$tabPlace($letpn,$i,statut)==$ok} { 
	    set nbPlaceOk [expr $nbPlaceOk+1]
	    set listePlace [linsert $listePlace end $tabPlace($letpn,$i,id)]
	    set vecteurM0  [linsert $vecteurM0 end $tabPlace($letpn,$i,jeton)]
	} else {
	    set listePlace [linsert $listePlace end "placedetruite"]
	}
    }

    
    for {set i 1} {$tabTransition($letpn,$i,statut)!=$fin}  {incr i} {
	set nbTransition [expr $nbTransition+1]
	set preT $vectNull
	set postT $vectNull
	if {$tabTransition($letpn,$i,statut)==$ok} {
	    set listeTransition [linsert $listeTransition end $tabTransition($letpn,$i,id)]
	    set nbTransitionOk [expr $nbTransitionOk+1]

	    for {set j 1} {$tabTransition($letpn,$i,Porg,$j) >0}   {incr j} {
		set indiceP [expr $tabTransition($letpn,$i,Porg,$j)-1]
		set preT [lreplace $preT $indiceP $indiceP $tabTransition($letpn,$i,PorgWeight,$j)]
	    }
	    for {set j 1} {$tabTransition($letpn,$i,Pdes,$j) >0}   {incr j} { 
		set indiceP [expr $tabTransition($letpn,$i,Pdes,$j)-1]
		set postT [lreplace $postT $indiceP $indiceP $tabTransition($letpn,$i,PdesWeight,$j)]
	    }
	    set matricePreT [linsert $matricePreT $i  $preT]
	    set matricePostT [linsert $matricePostT $i $postT]
	    set matriceCT [linsert $matriceCT $i [axpby_vect -1 $preT 1 $postT]]
	} 		    
    }


    set matricePreTotal [math::linearalgebra::transpose $matricePreT]
    set matricePostTotal [math::linearalgebra::transpose $matricePostT]
    set matriceCTotal [math::linearalgebra::transpose $matriceCT]
    set matricePre {}
    set matricePost {}
    set matriceC {}
    set listePlaceOk {}
    for {set i 0} {$i<$nbPlace} {incr i} {
	if {[lindex $listePlace $i]!="placedetruite"} {
	    set matriceC [linsert $matriceC end [lindex $matriceCTotal $i]]
	    set matricePre [linsert $matricePre end [lindex $matricePreTotal $i]]
	    set matricePost [linsert $matricePost end [lindex $matricePostTotal $i]]
	    set listePlaceOk [linsert $listePlaceOk end [lindex $listePlace $i]]
	}
    }

    

    
    $fenetreAnalyseStruct.text insert end "  \n" surgris

    $fenetreAnalyseStruct.text insert end "Pre =  " rouge
    afficheMatrice $fenetreAnalyseStruct $listePlaceOk $listeTransition $matricePre

    $fenetreAnalyseStruct.text insert end "\nPost = " rouge
    afficheMatrice $fenetreAnalyseStruct $listePlaceOk $listeTransition $matricePost

    $fenetreAnalyseStruct.text insert end "\nC =    " rouge
    afficheMatrice $fenetreAnalyseStruct $listePlaceOk $listeTransition $matriceC

    $fenetreAnalyseStruct.text insert end "\nInitial Marking =    " rouge
    afficheMatrice $fenetreAnalyseStruct $listePlaceOk " " $vecteurM0
    $fenetreAnalyseStruct.text insert end "\n" 
    $fenetreAnalyseStruct.text insert end "  \n" surgris
    $fenetreAnalyseStruct.text insert end " P invariants: \n" rouge
    $fenetreAnalyseStruct.text insert end "[TorPinvariant $listePlaceOk $matriceC] \n" bleu
    $fenetreAnalyseStruct.text insert end "\n" 
    $fenetreAnalyseStruct.text insert end "  \n" surgris
    $fenetreAnalyseStruct.text insert end " T invariants: \n" rouge
    $fenetreAnalyseStruct.text insert end "[TorPinvariant $listeTransition $matriceCT] \n" bleu
}

proc afficheMatrice {fenetre lig col matrice} {
    set norows [llength $matrice]
    $fenetre.text insert end "$col \n" bleu
    for { set nrow 0 } { $nrow < $norows } { incr nrow } {
	set sweep_row [math::linearalgebra::getrow $matrice $nrow]
#	puts "[lindex $lig $nrow] $sweep_row"
	$fenetre.text insert end "  [lindex $lig $nrow]  " bleu
	$fenetre.text insert end "  [lindex $matrice $nrow] \n" 
    }
}



proc TorPinvariant {lTorP matrice} {
    set norows [llength $lTorP]
    set resultat "\n --> "
    set matriceResultat ""
    set matriceTinv [semiFlows $matrice]    
    set nbInvariant [llength $matriceTinv]
    set nbTorP  [llength $lTorP]
    set mul "."
    for { set indiceInv 0 } { $indiceInv < $nbInvariant } { incr indiceInv } {
	set resultatInvariant ""
	set vectInvariant [lindex $matriceTinv $indiceInv]
	set matriceResultat "$matriceResultat    \{[lrange $vectInvariant end-[expr $nbTorP-1] end]\} \n"
	set operateur ""
	for { set i 0 } { $i < $norows } { incr i } {
	    set coef  [lindex $vectInvariant end-$i]
	    if {$coef!=0} { 
		if {$coef==1} { 
		    set resultatInvariant " [lindex $lTorP end-$i] $operateur$resultatInvariant"
		} else {
		    set resultatInvariant " $coef$mul[lindex $lTorP end-$i] $operateur$resultatInvariant"
		}
		set operateur "+"
	    }
	}
	set resultat "$resultat $resultatInvariant \n     "
    }
    return $matriceResultat$resultat
}


proc semiFlows {matrice} {
    set nbIteration [llength [lindex $matrice 0] ]
    set norows [llength $matrice]
    for { set nrow 0 } { $nrow < $norows } { incr nrow } {
	set vecteurUnit ""
	set sweep_row [lindex $matrice $nrow]
	for { set i 0 } { $i < $norows } { incr i } {
	    if {$i==$nrow} {
		set vecteurUnit "$vecteurUnit 1"
	    } else {
		set vecteurUnit "$vecteurUnit 0"
	    }
	}
	set concatenation "$sweep_row$vecteurUnit"
	set matrice [lreplace $matrice $nrow $nrow $concatenation]
    }
    return [algoSemiFlows $nbIteration $matrice]
}

proc algoSemiFlows {nbIteration matrix} {

set AN {}
set AP {}
set A {}

for { set i 0 } { $i < $nbIteration } { incr i } {
    set AN {}
    set AP {}
    set A {}
    set norows [llength $matrix]
    
    for { set nrow 0 } { $nrow < $norows } { incr nrow } {
	set sweep_row [math::linearalgebra::getrow $matrix $nrow]
	set ai [lindex $sweep_row $i]
	if {$ai <0} {
	    set AN [linsert $AN 0 $sweep_row]
	} elseif {$ai >0} {
	    set AP [linsert $AP 0 $sweep_row]
	} else {
	    set A [linsert $A 0 $sweep_row]
	}	
    }
    set norowsAN [llength $AN]
    set norowsAP [llength $AP]
    for { set j 0 } { $j < $norowsAN } { incr j } {
	set row_j_AN   [math::linearalgebra::getrow $AN $j]
	set coefAN [lindex $row_j_AN $i]
	for { set k 0 } { $k < $norowsAP } { incr k } {
	    set row_k_AP   [math::linearalgebra::getrow $AP $k]
	    set coefAP [lindex $row_k_AP $i]
	    set nnorm [expr -$coefAN/[gcd $coefAN $coefAP]]
	    set pnorm [expr $coefAP/[gcd $coefAN $coefAP]]
	    set ligne [axpby_vect $nnorm $row_k_AP $pnorm $row_j_AN]
#	    puts "-$coefAN * $row_k_AP + $coefAP * $row_j_AN -> $ligne"
	    set A [linsert $A 0  $ligne]
	}
    }
    set matrix $A
 }
 
return $A
}

proc gcd {p q} {
    while 1 {
        if {![set p [expr {$p % $q}]]} {return [expr {$q>0?$q:-$q}]}
        if {![set q [expr {$q % $p}]]} {return [expr {$p>0?$p:-$p}]}
    }
}


proc affichere {} { 
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

}


proc stateSpace {} {
    global romeoPath zoneOuClasseSpace
    global cheminTemp computOption
    global plateforme
    global tabPlace tabTransition
    global fin ok 
    global nomRdP tpn projet typePN
    global stateSpacefileType stateinfigure convergence
global nbIterationForcedDirected force distanceMin

    set last [string first ".xml" $nomRdP($tpn(onglet))] 
    if {$last>=0} {
         set nomStateSpaceFile [string range $nomRdP($tpn(onglet)) 0 [expr $last -1]]  
    } else {
         set nomStateSpaceFile $nomRdP($tpn(onglet))
    }

    set stateSpacefileType pdf
    set reponse "$cheminTemp/mercutio.ans"
    set syntaxerror "$cheminTemp/mercutio.log"
    set ctsfile "$cheminTemp/ctsfile.cts"

    set fenetreEspace .fenetreState 
    catch {destroy $fenetreEspace} 
    toplevel $fenetreEspace

    wm title $fenetreEspace [mc "Romeo - State Space Computation"] 

    set fsc $fenetreEspace
    set fenetreStateSpace  $fsc.fen

#    package require math::libgv-tcl
    
    frame $fsc.option 
    pack $fsc.option  -side top -expand yes -fill y  -pady .5c -padx .5c 
 
#    label $fsc.option.label -text "Options: " 
 #   pack $fsc.option.label -side top

    button $fsc.option.accepter -text "  Compute state space  "  -font menufont \
		-command "computeStateSpace $fenetreStateSpace"
	
    pack $fsc.option.accepter -side top -expand 1

 
    frame $fsc.option.sep -relief ridge -bd 1 -height 2 
    pack $fsc.option.sep -side top -fill x -expand no 

    
checkbutton $fsc.option.textoudessin -text "Symbolic state in figure" -font menufont -variable stateinfigure \
	-relief flat -anchor w -selectcolor red
    
    #-command "basculeIndentiferNomPlace $fp.identifier.saisieId"


      pack $fsc.option.textoudessin -side top -fill x
    
    frame $fsc.option.bouton 
    pack $fsc.option.bouton  -side top -expand yes -fill y
    #-pady .5c -padx .5c 


    set fscob $fsc.option.bouton
   
    
    frame $fscob.gauche 
    pack $fscob.gauche  -side left -expand yes -fill y  -pady .5c -padx .5c 

    radiobutton $fscob.gauche.format3 -text "txt" -font menufont -variable stateSpacefileType \
	-relief flat  -value "txt"  -width 20 -anchor w 
    pack  $fscob.gauche.format3  -side top -pady 2 -anchor w -fill x 

    if {[catch {exec which dot}] == 0} {
        radiobutton $fscob.gauche.format2 -text "graphviz" -font menufont -variable stateSpacefileType \
	    -relief flat  -value "pdf"  -width 20 -anchor w
	pack  $fscob.gauche.format2  -side top -pady 2 -anchor w -fill x 
    }
    
    radiobutton $fscob.gauche.format -text "graphics (force-directed)" -font menufont -variable stateSpacefileType \
	-relief flat  -value "force"  -width 20 -anchor w 
    pack  $fscob.gauche.format  -side top -pady 2 -anchor w -fill x 
 
#    radiobutton $fscob.gauche.format2 -text "pdf" -variable stateSpacefileType \
#	    -relief flat  -value "pdf"  -width 20 -anchor w 
#    pack  $fscob.gauche.format2  -side top -pady 2 -anchor w -fill x 

    label $fscob.gauche.algolabel -text "Force-directed graph drawing" -font menufont
    pack $fscob.gauche.algolabel -side top
#     label $fscob.gauche.label -text "Iteration number"
 #     pack $fscob.gauche.label -side left
#      $fp.nom.label config -text Label:

  #   entry $fscob.gauche.saisie -justify left -textvariable nbIterationForcedDirected -relief sunken -width 7 -bg white
    #   pack $fscob.gauche.saisie -side left


    frame $fscob.gauche.nbIt 
    pack $fscob.gauche.nbIt  -side top -expand yes -fill y  
    label $fscob.gauche.nbIt.label -text "Iteration number" -font menufont
    pack $fscob.gauche.nbIt.label -side left
    entry $fscob.gauche.nbIt.saisie -justify left -textvariable nbIterationForcedDirected -font menufont -relief sunken -width 7 -bg white
    pack $fscob.gauche.nbIt.saisie -side left
    frame $fscob.gauche.force 
    pack $fscob.gauche.force  -side top -expand yes -fill y  
    label $fscob.gauche.force.label -text "Repulsive force" -font menufont
    pack $fscob.gauche.force.label -side left
    entry $fscob.gauche.force.saisie -justify left -textvariable force -font menufont -relief sunken -width 7 -bg white
    pack $fscob.gauche.force.saisie -side left
    frame $fscob.gauche.ressort 
    pack $fscob.gauche.ressort  -side top -expand yes -fill y  
    label $fscob.gauche.ressort.label -text "Constante ressort" -font menufont
    pack $fscob.gauche.ressort.label -side left
    entry $fscob.gauche.ressort.saisie -justify left -textvariable constante_ressort -font menufont -relief sunken -width 7 -bg white
    pack $fscob.gauche.ressort.saisie -side left
	
    frame $fscob.gauche.distanceMin 
    pack $fscob.gauche.distanceMin  -side top -expand yes -fill y  
    label $fscob.gauche.distanceMin.label -text "Minimal distance" -font menufont
    pack $fscob.gauche.distanceMin.label -side left
    entry $fscob.gauche.distanceMin.saisie -justify left -textvariable distanceMin -font menufont  -relief sunken -width 7 -bg white
    pack $fscob.gauche.distanceMin.saisie -side left
    
    



    

    frame $fscob.milieu 
    pack $fscob.milieu  -side left -expand yes -fill y  -pady .5c -padx .5c 

    
    radiobutton $fscob.milieu.classe -text "State class" -font menufont -variable zoneOuClasseSpace \
	    -relief flat  -value 0  -width 20 -anchor w 
 
    radiobutton $fscob.milieu.zone -text "Zone" -font menufont -variable zoneOuClasseSpace \
	    -relief flat  -value 1  -width 20 -anchor w 
 
 
    pack  $fscob.milieu.classe  -side top -pady 2 -anchor w -fill x 
    pack  $fscob.milieu.zone  -side top -pady 2 -anchor w -fill x 


    frame $fscob.droite 
    pack $fscob.droite  -side left -expand yes -fill y  -pady .5c -padx .5c 

        label  $fscob.droite.label -text "Convergence criterion " -font menufont
    pack  $fscob.droite.label -side top 

    radiobutton $fscob.droite.inclusion -text "inclusion" -font menufont -variable convergence \
	    -relief flat  -value 0  -anchor w 
 
    radiobutton $fscob.droite.egalite -text "equality" -font menufont -variable convergence \
	-relief flat  -value 1   -anchor w

    radiobutton $fscob.droite.merge -text "merge" -font menufont -variable convergence \
	-relief flat  -value 2   -anchor w

    pack  $fscob.droite.inclusion  -side top -pady 2 -anchor w -fill x 
    pack  $fscob.droite.egalite  -side top -pady 2 -anchor w -fill x 
    pack  $fscob.droite.merge  -side top -pady 2 -anchor w -fill x 
    
}

proc computeStateSpace {fenetreStateSpace} {
    global romeoPath zoneOuClasseSpace
    global cheminTemp computOption
    global plateforme typePN
    global tabPlace tabTransition
    global fin ok 
    global nomRdP tpn projet
    global stateSpacefileType stateinfigure convergence
    global nbIterationForcedDirected force distanceMin

       set last [string first ".xml" $nomRdP($tpn(onglet))] 
    if {$last>=0} {
         set nomStateSpaceFile [string range $nomRdP($tpn(onglet)) 0 [expr $last -1]]  
    } else {
         set nomStateSpaceFile $nomRdP($tpn(onglet))
    }

    set nomStateSpaceFilePdf $nomStateSpaceFile.pdf
 
    
    destroy $fenetreStateSpace
    frame $fenetreStateSpace 
    pack $fenetreStateSpace -side top 
    
    text $fenetreStateSpace.text -yscrollcommand "$fenetreStateSpace.scroll set" -setgrid true \
	-width 80 -height 40 -wrap word -bg white -font fontEditor
    scrollbar $fenetreStateSpace.scroll -command "$fenetreStateSpace.text yview" 
     
    pack $fenetreStateSpace.scroll -side right -fill y 
     
    pack $fenetreStateSpace.text -expand yes -fill both 
    $fenetreStateSpace.text tag configure rouge -foreground red 
    $fenetreStateSpace.text tag configure bleu -foreground blue 
    $fenetreStateSpace.text tag configure surgris -background #a0b7ce 
    $fenetreStateSpace.text tag configure souligne -underline on 
 
 
	#************************************** 
    $fenetreStateSpace.text insert end "Petri net : [nomSeul $nomRdP($tpn(onglet))] \n"

    if {$typePN==2} {
	$fenetreStateSpace.text insert end " \n" 
	$fenetreStateSpace.text insert end "State space computation not available for P-TPN ! \n \n" rouge
	$fenetreStateSpace.text insert end "The state space will be computed on " bleu
	$fenetreStateSpace.text insert end " untimed(" rouge
	$fenetreStateSpace.text insert end "[nomSeul $nomRdP($tpn(onglet))]" rougebleu
	$fenetreStateSpace.text insert end ") \n" rouge
    }

    $fenetreStateSpace.text insert end " \n" 
    $fenetreStateSpace.text insert end " \n" surgris

    set last [string first ".xml" $nomRdP($tpn(onglet))] 
    if {$last>=0} {
         set nomStateSpaceFile [string range $nomRdP($tpn(onglet)) 0 [expr $last -1]]  
    } else {
         set nomStateSpaceFile $nomRdP($tpn(onglet))
    }
    
    set point "."
    set nomStateSpaceFile $nomStateSpaceFile$point$stateSpacefileType

    
    set reponse "$cheminTemp/mercutio.ans"
    set syntaxerror "$cheminTemp/mercutio.log"
    set ctsfile "$cheminTemp/ctsfile.cts"

    set tpn(courant) [calculTPNCourant 0]

    set virgule ""
    set option ""
    if {$convergence==0} {
	set option "passed=inc"
	set virgule ","
    } elseif {$convergence==1} {
	set option "passed=eq"
	set virgule ","
    }
    if {$zoneOuClasseSpace}   {
	set option "$option$virgule zones"
	set virgule ","
    } 
    if {$stateinfigure==0}  {set option "$option$virgule nodes = out"} 
    #nodes = out
    
    if {$option==""} { set espaceEtats "graph"} else {set espaceEtats "graph \[$option\]"}
    export2CTS $tpn(courant) $ctsfile $espaceEtats 0

    set executable $romeoPath
    append executable "bin/romeo-cli"
    if {[string compare $plateforme "windows"]==0} {
	append executable ".exe"
    }


    # effacer ce qu'il y a dans le fichier de log
    if {[file exists $syntaxerror]} {
	set File [open $syntaxerror w+]
	close $File
    }
   
   if { [catch {exec $executable -v -m $ctsfile > $reponse 2>> $syntaxerror} erreur] } {

#	puts $erreur
       if {(![file exists $syntaxerror])||[emptyFile $syntaxerror]} {
	   if { ![catch {open $syntaxerror w} fid] } {
	       set File [open $syntaxerror w]
	       puts $File "$erreur"
	       close $File
	  }
       }
   } else {
       set leGraphe ""
       set symbolicState ""
       set basculestateinfigure 0
       if { ![catch {open $reponse r} fid] } {
	   set File [open $reponse r]
	   while {![eof $File]} {
	       gets $File line
	       if {([string compare  [nextExpression $line " "] "\[info\]"]!=0)&&([string compare  [nextExpression $line " "] "\[warning\]"]!=0)} {
		   if {[string compare  [nextExpression $line \n] "--------------------------------------------------------------------------------"]==0} {
		       set basculestateinfigure 1
		   }

		   if {$basculestateinfigure} {
		       set symbolicState "$symbolicState $line\n"
		   } else {
		       set leGraphe "$leGraphe $line\n"
		   }
	       }
	   }
	   close $File
	   set File [open $reponse w]
	   flush $File
	   puts $File $leGraphe
	   close $File 
	   if {$stateSpacefileType=="txt"} {
	       affiche "\n-Computing state space ($espaceEtats) in : [nomSeul $nomStateSpaceFile] " 
	       $fenetreStateSpace.text insert end "\nComputing state space ($espaceEtats) in : [nomSeul $nomStateSpaceFile] \n" 
	       set File [open $nomStateSpaceFile w]
	       flush $File
	       puts $File $leGraphe
	       puts $File $symbolicState
	       close $File
	       $fenetreStateSpace.text insert end "State space is given in Graphviz text format: \n\n" bleu
	       $fenetreStateSpace.text insert end "\n" surgris
	       $fenetreStateSpace.text insert end "\n \n$leGraphe" 
	       $fenetreStateSpace.text insert end "\n \n$symbolicState" 
	   } elseif {$stateSpacefileType=="pdf"} {
	       if {![catch {exec [exec which dot] -T pdf -o $nomStateSpaceFilePdf $reponse} erreur] } {
		   affiche "\n-Computing state space in : [nomSeul $nomStateSpaceFile] " 
		   $fenetreStateSpace.text insert end "\nComputing state space ($espaceEtats) in : [nomSeul $nomStateSpaceFilePdf] \n" bleu
		   if {	![catch {exec open $nomStateSpaceFilePdf}]} {
		       $fenetreStateSpace.text insert end "Opening file \n"
		       if {$stateinfigure==0} {
			   $fenetreStateSpace.text insert end "\n"
			   $fenetreStateSpace.text insert end "Symbolic states\n" surgris
			   $fenetreStateSpace.text insert end $symbolicState
		       }
		   }
	       } else {
		   affiche "\n Unable to load graphviz"
		   $fenetreStateSpace.text insert end "\n Unable to load graphviz \n" bleu
	       }
	   } else { 
	       $fenetreStateSpace.text insert end "\nComputing state space ($espaceEtats)" bleu
	       $fenetreStateSpace.text insert end "\n" surgris
	       $fenetreStateSpace.text insert end "\nTrying to compute the graph with force-directed algorithm \n" bleu
#	       $fenetreStateSpace.text insert end "\nError in invoking Graphviz \n" bleu
#	       $fenetreStateSpace.text insert end "State space is given in Graphviz text format: \n\n" bleu
#	       $fenetreStateSpace.text insert end "\n" surgris

	       if {[string is integer -strict $nbIterationForcedDirected]&&( $nbIterationForcedDirected > 0)&& [string is integer -strict $force]&&[string is integer -strict $distanceMin] } {

#		       if {$stateinfigure} {
#			   set force_repulsion 100000
#			   set distMin 180
#		       } else {
#			   set force_repulsion 20000
#			   set distMin 30
#		       }
		   calculerGrapheStateSpace $leGraphe $stateinfigure $nbIterationForcedDirected $force $distanceMin
	       } else {       
		   $fenetreStateSpace.text insert end "\n -> Paramaters must be integer >0\n" rouge
		   $fenetreStateSpace.text insert end "\n" surgris

	       }
	       if {$stateinfigure} {
		   $fenetreStateSpace.text insert end "\n \n$leGraphe" 
		   $fenetreStateSpace.text insert end "\n \n$symbolicState"
	       } else {
		   $fenetreStateSpace.text insert end "\n \n$symbolicState"
		   $fenetreStateSpace.text insert end "\n \n$leGraphe" 
	       }

	   }
#	   else {
#	       affiche "\n-Computing state space in : [nomSeul $nomStateSpaceFile] " 
#	       $fenetreStateSpace.text insert end "\nComputing state space ($espaceEtats) in : [nomSeul $nomStateSpaceFile] \n" bleu
#	       if {	![catch {exec open $nomStateSpaceFile}]} {
#		   $fenetreStateSpace.text insert end "Opening file \n"
#		   if {$stateinfigure==0} {
#		       $fenetreStateSpace.text insert end "\n"
#		       $fenetreStateSpace.text insert end "Symbolic states\n" surgris
#		       $fenetreStateSpace.text insert end $symbolicState
#		   }
#	       } else {
#		   $fenetreStateSpace.text insert end "Unabled to open  $nomStateSpaceFile"
#		   $fenetreStateSpace.text insert end "State space is given in Graphviz text format: \n\n" bleu
#		   $fenetreStateSpace.text insert end "\n" surgris
#		   $fenetreStateSpace.text insert end "\n \n$leGraphe" 
#		   $fenetreStateSpace.text insert end "\n \n$symbolicState" 
#	       }	      
#	   }
       }
   }
#   afficheCheck $fenetreStateSpace.text 0 0

#!/usr/local/bin/tclsh
#package require Tcldot

   
}

proc tcl_to_python_list {tcl_list} {
    set python_list "\["  ;# Utiliser des \[ pour l'ouverture du [ dans une chaîne

    foreach item $tcl_list {
        if {[string is double -strict $item]} {
            append python_list "$item,"
        } else {
            set escaped_item [string map {\" \\\" \\ \\\\} $item]
            append python_list "\"$escaped_item\","
        }
    }

    if {[string length $python_list] > 1} {
        set python_list [string range $python_list 0 end-1]
    }
    append python_list "\]"

    return $python_list
}

proc tcl_to_python_list_of_lists {tcl_list_of_lists} {
    set python_list "\["

    foreach sublist $tcl_list_of_lists {
        append python_list "[string trim [tcl_to_python_list $sublist]]"
        append python_list ","
    }

    if {[string length $python_list] > 1} {
        set python_list [string range $python_list 0 end-1]
    }
    append python_list "\]"

    return $python_list
}


proc   exporterMatrice {} {
    global nomRdP 
    global tpn 
    global cheminFichiers
    global matricePre matricePost matriceCT vecteurM0 listeTransition

	set types { 
	    {{[mc "File"]}     {.txt}      TEXT} 
	} 
    if [string compare "$nomRdP($tpn(onglet))" "noName.xml"] {
	set fichier  "[sansXml $nomRdP($tpn(onglet))]_matrix.txt"
#	    set fichier [tk_getSaveFile -filetypes $types  -title [mc "Save matrices as"] \
#			     -initialdir [repertoire $nomRdP($tpn(onglet))] -initialfile [nomSeul $nomRdP($tpn(onglet))] -defaultextension .txt] 
	} else { 
	    set fichier [tk_getSaveFile -filetypes $types  -title [mc "Save matrix as"] \
			     -initialdir "$cheminFichiers" -initialfile [sansXml $nomRdP($tpn(onglet))]_matrix.txt -defaultextension .txt] 
	     
	} 
    if { ![catch {open $fichier w} fid] } {
	affiche "\n-Save matrix as "
	afficheBleu "$fichier"
	set File [open $fichier w]
#	puts $File [tcl_to_python_list $listeTransition]
	puts $File  $listeTransition
	puts $File [tcl_to_python_list_of_lists $matricePre]
	puts $File [tcl_to_python_list_of_lists $matricePost]
	puts $File [tcl_to_python_list $vecteurM0]
#	   puts  [tcl_to_python_list_of_lists $matricePre]
#	   puts  [tcl_to_python_list_of_lists $matricePost]
	      close $File 
	  }	   
}
   
