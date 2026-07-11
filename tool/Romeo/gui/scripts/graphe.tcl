proc wrap_label {input maxlen} {
    set lines [split $input "\n"]
    set wrapped_lines {}

    foreach line $lines {
        set words [split $line " "]
        set current ""

        foreach word $words {
            if {[string length "$current $word"] <= $maxlen} {
                if {$current eq ""} {
                    set current $word
                } else {
                    append current " $word"
                }
            } else {
                lappend wrapped_lines $current
                set current $word
            }
        }

        if {$current ne ""} {
            lappend wrapped_lines $current
        }
    }

    return [join $wrapped_lines "\n"]
}

# Fonction pour analyser un graphe orienté au format DOT simplifié

# Analyse les sommets avec label


proc analyserSommets {texte_dot ClasseInSide} {
    array set etiquettes {}
    set lignes [split $texte_dot "\n"]

    set bloc ""
    set in_bloc 0
    set identifiant ""

    array set sommets_vus {}

    foreach ligne $lignes {
        set ligne [string trim $ligne]

        # Cas 1 : arêtes (dirigées ou non dirigées)
        if {[regexp {([a-zA-Z0-9_]+)\s*[-]{1,2}>\s*([a-zA-Z0-9_]+)} $ligne _ src dst] || 
            [regexp {([a-zA-Z0-9_]+)\s*--\s*([a-zA-Z0-9_]+)} $ligne _ src dst]} {
            set sommets_vus($src) 1
            set sommets_vus($dst) 1
        }

        # Cas 2 : début de bloc attributs
        if {!$in_bloc && [regexp {^([a-zA-Z0-9_]+)\s*\[} $ligne _ id]} {
            set identifiant $id
            set bloc "$ligne\n"
            set in_bloc 1
            continue
        }

        # Cas 3 : bloc attributs en cours
        if {$in_bloc} {
            append bloc "$ligne\n"

            if {[string match "*];" $ligne]} {
                set sommets_vus($identifiant) 1
                if {$ClasseInSide && [regexp {label\s*=\s*"((?:[^"\\]|\\.)*)"} $bloc _ label_brut]} {
                    set label [string map {"\\n" "\n"} $label_brut]
#" juste pour l'editeur	
                    set label [wrap_label $label 20]
		set etiquettes($identifiant) $label
                } else {
                    set etiquettes($identifiant) $identifiant
                }
                set bloc ""
                set in_bloc 0
                set identifiant ""
            }
            continue
        }

        # Cas 4 : sommet seul sans attributs
        if {[regexp {^([a-zA-Z0-9_]+)\s*;} $ligne _ sommet_seul]} {
            set sommets_vus($sommet_seul) 1
            if {![info exists etiquettes($sommet_seul)]} {
                set etiquettes($sommet_seul) $sommet_seul
            }
        }
    }

    # Compléter avec tous les sommets vus sans labels
    foreach sommet [array names sommets_vus] {
        if {![info exists etiquettes($sommet)]} {
            set etiquettes($sommet) $sommet
        }
    }

    return [array get etiquettes]
}


	

proc analyserDOT {texte_dot} {
    set arcs {}
    foreach ligne [split $texte_dot "\n"] {
        set ligne [string trim $ligne " \t\r\n;"]

        # Regex mise à jour pour tolérer les espaces avant/entre crochets
        if {[regexp {^([a-zA-Z0-9_]+)\s*->\s*([a-zA-Z0-9_]+)\s*(?:\[\s*label\s*=\s*"(.*?)"\s*\])?} $ligne -> sommet1 sommet2 label]} {
            if {$label eq ""} {
                set label "$sommet1→$sommet2"
            }
            lappend arcs [list $sommet1 $sommet2 $label]
        }
    }
    return $arcs
}




# Fonction pour dessiner le graphe
# Fonction pour ajuster dynamiquement la taille de la police en fonction du facteur de zoom
# Fonction pour ajuster dynamiquement la taille de la police en fonction du facteur de zoom


# Zoom
proc zoomCanvas {canvas x y direction} {
    # Calcul du facteur de zoom
    if {$direction > 0} {
        set scale 1.1
    } else {
        set scale 0.9
    }

    # Mettre à jour le facteur global de zoom
    set ::zoomFactor [expr {$::zoomFactor * $scale}]

    # Appliquer le zoom visuel sur les éléments existants (optionnel si on redessine tout)
    $canvas scale all $x $y $scale $scale

    # Mettre à jour la région de scroll du canvas
    set bbox [$canvas bbox all]
    if {$bbox ne ""} {
        $canvas configure -scrollregion $bbox
    }

    # Redessiner tout le graphe proprement à la nouvelle échelle
    RedessinerGraphe
}


proc calculerGrapheStateSpace {texte_dot ClasseInSide iterations force_repulsion distMin} {



    calculerGraphe $texte_dot $ClasseInSide $iterations $force_repulsion $distMin
# foreach s $::sommets {
 #       puts "$s $::position($s)"
  #  }

    initialiserCanvasStateSpace
}

# Fonction principale
proc calculerGraphe {texte_dot ClasseInSide iterations force_repulsion distMin} {
    # Sauvegarde pour redessin
    set ::lastClasseInSide $ClasseInSide
    set ::lastIterations $iterations
    set ::lastTexteDOT $texte_dot

    # Zoom initial
    if {![info exists ::zoomFactor]} {
        set ::zoomFactor 1.0
    }

    # Paramètres de dessin
    set seuil_zoom 2.0

    if {$ClasseInSide} {
	set distMin [expr $distMin+120]
        set ::rayon 40
    } else {
        set ::rayon 12
    }

    # Analyse DOT
  #  set etiquettes_sommets [analyserSommets $texte_dot $ClasseInSide]
  #  array set ::etiquette $etiquettes_sommets
    array set ::etiquette [analyserSommets $texte_dot $ClasseInSide]
    set tous_les_sommets [array names etiquettes]

    
    set ::arcs [analyserDOT $texte_dot]

    # Extraire sommets

   set sommets_connectes {}
    foreach arc $::arcs {
	lassign $arc depart arrivee
	lappend sommets_connectes $depart $arrivee
    }
    set sommets_connectes [lsort -unique $sommets_connectes]

    set ::sommets [lsort -unique [concat $tous_les_sommets $sommets_connectes]]
#    set ::sommets [lsort -unique $sommets]

    # Positions aléatoires
    foreach s $::sommets {
        set ::position($s) [list [expr {50 + int(rand()*$::largeur_visible)}] [expr {50 + int(rand()*$::hauteur_visible)}]]
    }

    # Algorithme force-directed
    for {set i 0} {$i < $iterations} {incr i} {
        array set deplacementX {}
        array set deplacementY {}
        foreach s $::sommets {
            set deplacementX($s) 0
            set deplacementY($s) 0
        }

        foreach s1 $::sommets {
            foreach s2 $::sommets {
                if {$s1 eq $s2} continue
                lassign $::position($s1) x1 y1
                lassign $::position($s2) x2 y2
                set dx [expr {$x1 - $x2}]
                set dy [expr {$y1 - $y2}]
                set distance [expr {max(sqrt($dx*$dx + $dy*$dy), $distMin)}]
                set force [expr {$force_repulsion / pow($distance, 1.5)}]
                set deplacementX($s1) [expr {$deplacementX($s1) + ($dx / $distance) * $force}]
                set deplacementY($s1) [expr {$deplacementY($s1) + ($dy / $distance) * $force}]
            }
        }

        foreach arc $::arcs {
            lassign $arc s1 s2
            lassign $::position($s1) x1 y1
            lassign $::position($s2) x2 y2
            set dx [expr {$x2 - $x1}]
            set dy [expr {$y2 - $y1}]
            set distance [expr {max(sqrt($dx*$dx + $dy*$dy), $distMin)}]
            set force [expr {$distance * $distance / $::constante_ressort}]
            set fx [expr {($dx / $distance) * $force}]
            set fy [expr {($dy / $distance) * $force}]
            set deplacementX($s1) [expr {$deplacementX($s1) + $fx}]
            set deplacementY($s1) [expr {$deplacementY($s1) + $fy}]
            set deplacementX($s2) [expr {$deplacementX($s2) - $fx}]
            set deplacementY($s2) [expr {$deplacementY($s2) - $fy}]
        }

        foreach s $::sommets {
            lassign $::position($s) x y
            set dx $deplacementX($s)
            set dy $deplacementY($s)
            set dist [expr {sqrt($dx*$dx + $dy*$dy)}]
            set facteur [expr {$dist > 10 ? 10 : $dist}]
            if {$dist > 0} {
                set x [expr {$x + ($dx / $dist) * $facteur}]
                set y [expr {$y + ($dy / $dist) * $facteur}]
            }
            set x [expr {min(max($x, 20), 2580)}]
            set y [expr {min(max($y, 20), 2580)}]
            set ::position($s) [list $x $y]
        }
    }

    # Centrage
    set minX 2600
    set minY 2600
    set maxX 2600
    set maxY 2600
    foreach s $::sommets {
        lassign $::position($s) x y
        if {$x < $minX} { set minX $x }
        if {$y < $minY} { set minY $y }
        if {$x > $maxX} { set maxX $x }
        if {$y > $maxY} { set maxY $y }
    }
    set marge [expr {$::rayon + 10}]
    set dx [expr {-$minX + $marge}]
    set dy [expr {-$minY + $marge}]
    foreach s $::sommets {
        lassign $::position($s) x y
        set ::position($s) [list [expr {$x + $dx}] [expr {$y + $dy}]]
    }
    set ::largeur_totale [expr $maxX+$dx+2*$marge]
    set ::hauteur_totale [expr $maxY+$dy+2*$marge]

}

#*****************************
proc initialiserCanvasStateSpace {} {
    global nomRdP tpn

    set last [string first ".xml" $nomRdP($tpn(onglet))] 
    if {$last>=0} {
         set nomStateSpaceFile [string range $nomRdP($tpn(onglet)) 0 [expr $last -1]]  
    } else {
         set nomStateSpaceFile $nomRdP($tpn(onglet))
    }

    
    # Créer l'interface (une seule fois)
    set f .stateSpace
    catch {destroy $f}
    toplevel $f
    frame $f.cadre
    scrollbar $f.cadre.vscroll -orient vertical -command "$f.cadre.canvas yview"
    scrollbar $f.cadre.hscroll -orient horizontal -command "$f.cadre.canvas xview"
    canvas $f.cadre.canvas -width $::largeur_visible -height $::hauteur_visible \
        -scrollregion "0 0 $::largeur_totale $::hauteur_totale" \
        -xscrollcommand "$f.cadre.hscroll set" \
        -yscrollcommand "$f.cadre.vscroll set" \
        -bg white
    grid $f.cadre.canvas -row 0 -column 0 -sticky news
    grid $f.cadre.vscroll -row 0 -column 1 -sticky ns
    grid $f.cadre.hscroll -row 1 -column 0 -sticky ew
    grid rowconfigure $f.cadre 0 -weight 1
    grid columnconfigure $f.cadre 0 -weight 1
    pack $f.cadre -fill both -expand 1

    bind $f.cadre.canvas <MouseWheel> [list apply {{w d x y} {
        zoomCanvas $w $x $y $d
    }} %W %D %x %y]

    frame $f.zoomControls
    button $f.zoomControls.zoomIn -text "Zoom +" -command [list zoomCanvas $f.cadre.canvas 400 300 1]
    button $f.zoomControls.zoomOut -text "Zoom -" -command [list zoomCanvas $f.cadre.canvas 400 300 -1]

    button $f.zoomControls.jpeg -text "Export as postscript" -command "exportAsPS $f $nomStateSpaceFile"

    pack $f.zoomControls.zoomIn $f.zoomControls.zoomOut -side left -padx 5 -pady 5
    pack $f.zoomControls.jpeg  -side right -padx 5 -pady 5
    pack $f.zoomControls -side bottom -fill x

    # Redessiner le graphe
    RedessinerGraphe
}
#*******************************


proc RedessinerGraphe {} {
    set canvas .stateSpace.cadre.canvas
    $canvas delete all

    set facteur $::zoomFactor
    set rayon [expr {$::rayon * $facteur}]

    # Dessin des arcs
    foreach arc $::arcs {
        lassign $arc s1 s2 label
        lassign $::position($s1) x1 y1
        lassign $::position($s2) x2 y2

        # Appliquer zoom
        set x1z [expr {$x1 * $facteur}]
        set y1z [expr {$y1 * $facteur}]
        set x2z [expr {$x2 * $facteur}]
        set y2z [expr {$y2 * $facteur}]

        set dx [expr {$x2z - $x1z}]
        set dy [expr {$y2z - $y1z}]
        set distance [expr {sqrt($dx*$dx + $dy*$dy)}]
        if {$distance == 0} { set distance 0.1 }
	set dxn [expr {$dx == 0 ? 0.1 : $dx / $distance}]
	set dyn [expr {$dy == 0 ? 0.1 : $dy / $distance}]
#set dxn [expr {$dx / $distance}]
#        set dyn [expr {$dy / $distance}]
        set scale [expr {min($rayon / abs($dxn), $rayon / abs($dyn))}]

	
        set x1b [expr {$x1z + $dxn * $scale}]
        set y1b [expr {$y1z + $dyn * $scale}]
        set x2b [expr {$x2z - $dxn * $scale}]
        set y2b [expr {$y2z - $dyn * $scale}]

        # Dessiner la ligne fléchée
        $canvas create line $x1b $y1b $x2b $y2b -arrow last -width 2 -fill gray

        # Position du label
        set x_label [expr {($x1b + $x2b)/2.0}]
        set y_label [expr {($y1b + $y2b)/2.0}]
        set offset 10
        set x_label [expr {$x_label + ($dy / $distance) * $offset}]
        set y_label [expr {$y_label - ($dx / $distance) * $offset}]
        $canvas create text $x_label $y_label -text $label -font "Helvetica 10 italic" -fill black
    }

    # Dessin des sommets
    foreach s $::sommets {
        lassign $::position($s) x y

        set zx [expr {$x * $facteur}]
        set zy [expr {$y * $facteur}]

        $canvas create rectangle \
            [expr {$zx - $rayon}] [expr {$zy - $rayon}] \
            [expr {$zx + $rayon}] [expr {$zy + $rayon}] \
            -fill lightblue -outline black

        # Déterminer le texte du sommet
        set texte [expr {($::lastClasseInSide && [info exists ::etiquette($s)]) ? $::etiquette($s) : $s}]

        # Taille de la police adaptée
        set fontSize [expr {max(1, min(30, int(8 * $facteur)))}]

        $canvas create text $zx $zy -text $texte -font "Helvetica $fontSize bold"
    }

    # Mise à jour de la scrollregion
    set bbox [$canvas bbox all]
    if {$bbox ne ""} {
        $canvas configure -scrollregion $bbox
    }
}

#******************************* placer les sommets du RDP *********************

proc fautIlPlacer {leTexte} {
    global romeoPath zoneOuClasseSpace
    global cheminTemp computOption
    global tabPlace tabTransition
    global fin ok 
    global nomRdP tpn projet typePN
    global nbIterationForcedDirected force distanceMin


    if {$leTexte} {
	set leTexte "Auto Drawing"
    } else {
    	set leTexte "No graphical data"
}
    set last [string first ".xml" $nomRdP($tpn(onglet))] 
    if {$last>=0} {
         set nomStateSpaceFile [string range $nomRdP($tpn(onglet)) 0 [expr $last -1]]  
    } else {
         set nomStateSpaceFile $nomRdP($tpn(onglet))
    }

    
    set PNdrawing .fenetrePNdrawing 
    catch {destroy $PNdrawing} 
    toplevel $PNdrawing

    wm title $PNdrawing [mc "Graphical data"]

#    set fsc $fenetreEspace
 #   set fenetreStateSpace  $fsc.fen

#    package require math::libgv-tcl
    
    frame $PNdrawing.texte 
    pack $PNdrawing.texte  -side top -expand yes -fill y  -pady .5c -padx .5c 
 
    label $PNdrawing.texte.label1 -text "$leTexte" 
    pack $PNdrawing.texte.label1 -side top

    label $PNdrawing.texte.label2 -text "Would you like an automatic drawing ? " 
    pack $PNdrawing.texte.label2 -side top

 
    frame $PNdrawing.sep1 -relief ridge -bd 1 -height 2 
    pack $PNdrawing.sep1 -side top -fill x -expand no 

    

     label $PNdrawing.algolabel -text "Force-directed graph drawing"
     pack $PNdrawing.algolabel -side top



    frame $PNdrawing.nbIt 
    pack $PNdrawing.nbIt  -side top -expand yes -fill y  
    label $PNdrawing.nbIt.label -text "Iteration number"
    pack $PNdrawing.nbIt.label -side left
    entry $PNdrawing.nbIt.saisie -justify left -textvariable nbIterationForcedDirected -relief sunken -width 7 -bg white
    pack $PNdrawing.nbIt.saisie -side left
    frame $PNdrawing.force 
    pack $PNdrawing.force  -side top -expand yes -fill y  
    label $PNdrawing.force.label -text "Repulsive force"
    pack $PNdrawing.force.label -side left
    entry $PNdrawing.force.saisie -justify left -textvariable force -relief sunken -width 7 -bg white
    pack $PNdrawing.force.saisie -side left
    frame $PNdrawing.ressort 
    pack $PNdrawing.ressort  -side top -expand yes -fill y  
    label $PNdrawing.ressort.label -text "Constante ressort"
    pack $PNdrawing.ressort.label -side left
    entry $PNdrawing.ressort.saisie -justify left -textvariable constante_ressort -relief sunken -width 7 -bg white
    pack $PNdrawing.ressort.saisie -side left
    frame $PNdrawing.distanceMin 
    pack $PNdrawing.distanceMin  -side top -expand yes -fill y  
    label $PNdrawing.distanceMin.label -text "Minimal distance"
    pack $PNdrawing.distanceMin.label -side left
    entry $PNdrawing.distanceMin.saisie -justify left -textvariable distanceMin -relief sunken -width 7 -bg white
    pack $PNdrawing.distanceMin.saisie -side left

        frame $PNdrawing.sep2 -relief ridge -bd 1 -height 2 
    pack $PNdrawing.sep2 -side top -fill x -expand no 


    	bind $PNdrawing <Return> "algoDrawingPN $PNdrawing"
	bind $PNdrawing <Escape> "cancelalgoDrawingPN $PNdrawing"
	frame $PNdrawing.buttons
	pack $PNdrawing.buttons -side bottom -fill x -pady 2m

    bind $PNdrawing <Return> "destroy $PNdrawing"
    button $PNdrawing.buttons.annuler -text Cancel -command  "cancelalgoDrawingPN $PNdrawing"
    button $PNdrawing.buttons.accepter -default active -text "  Ok  " \
	-command "algoDrawingPN $PNdrawing"

    pack $PNdrawing.buttons.accepter $PNdrawing.buttons.annuler  -side left -expand 1

    
}

proc algoDrawingPN {PNdrawing} {
    global tabPlace tabTransition
    global fin ok 
    global nomRdP tpn projet typePN
    global nbIterationForcedDirected force distanceMin

  

    modifTPN $tpn(courant)

    set ledigraphe ""

    
   for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
       if {$tabTransition($tpn(courant),$i,statut) == $ok} {
	   set notConnected 1
	   for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} {
	       set ledigraphe "$ledigraphe P$tabTransition($tpn(courant),$i,Porg,$j) -> T$i ;\n"
	       set notConnected 0
	   }
	   for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} {
	       set ledigraphe "$ledigraphe T$i -> P$tabTransition($tpn(courant),$i,Pdes,$j) ;\n"
	       set notConnected 0
	   }
	   if {$notConnected} {
	       set ledigraphe "$ledigraphe T$i ;\n"
	   }
       }
   }

    if {[string is integer -strict $nbIterationForcedDirected]&&( $nbIterationForcedDirected > 0)&& [string is integer -strict $force]&&[string is integer -strict $distanceMin] } {
   calculerGraphe $ledigraphe  0 $nbIterationForcedDirected $force $distanceMin
#	calculerGrapheStateSpace $ledigraphe  0 $nbIterationForcedDirected $force $distanceMin
	for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
	    if {$tabTransition($tpn(courant),$i,statut) == $ok} {
		set tabTransition($tpn(courant),$i,xy,x) [lindex $::position(T$i) 0]
		set tabTransition($tpn(courant),$i,xy,y) [lindex $::position(T$i) 1]
	    }
	}
	for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin}  {incr i} {
	    if {$tabPlace($tpn(courant),$i,statut) == $ok} {
		set tabPlace($tpn(courant),$i,xy,x) [lindex $::position(P$i) 0]
		set tabPlace($tpn(courant),$i,xy,y) [lindex $::position(P$i) 1]
	    }
	}
	
    }
    ajusteTaille

    destroy $PNdrawing
    redessinerProjet .romeo.global

}

proc cancelalgoDrawingPN {PNdrawing} {

    destroy $PNdrawing
    redessinerProjet .romeo.global
    affiche [mc "done"]

    
}

proc absenceDonneesGraphiques {} {
    global tabPlace tabTransition
    global tpn
    global fin ok
    
    set existeInfo 1
	for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
	    if {$tabTransition($tpn(courant),$i,statut) == $ok} {
		if {(($tabTransition($tpn(courant),$i,xy,x)!=0)&&($tabTransition($tpn(courant),$i,xy,x)!=100))||(($tabTransition($tpn(courant),$i,xy,y)!=0)&&($tabTransition($tpn(courant),$i,xy,y)!=100))} {
		    set existeInfo 0
		}
	    }
	}
	for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin}  {incr i} {
	    if {$tabPlace($tpn(courant),$i,statut) == $ok} {
		if {(($tabPlace($tpn(courant),$i,xy,x)!=0)&&($tabPlace($tpn(courant),$i,xy,x)!=100))||(($tabPlace($tpn(courant),$i,xy,y)!=0)&&($tabPlace($tpn(courant),$i,xy,y)!=100))} {
		    set existeInfo 0
		}
	    }
	}
    return $existeInfo
}

proc exportAsPS {f fichier} {

    # Appliquer le zoom visuel sur les éléments existants (optionnel si on redessine tout)
set scale1 [expr 1.0*$::largeur_visible/$::largeur_totale]
set scale2 [expr 1.0*$::hauteur_visible/$::hauteur_totale]
#set scale1 [expr 0.65*$width/$::largeur_totale]
#set scale2 [expr 0.65*$height/$::hauteur_totale]

set scale [expr {$scale1 < $scale2 ? $scale1 : $scale2}]

set ::zoomFactor [expr $scale/1.4]

#.stateSpace.cadre.canvas scale all 0 0 $scale $scale
RedessinerGraphe

# Redimensionner le canvas à la taille complète
#.stateSpace.cadre.canvas configure -width $::largeur_totale -height $::hauteur_totale 

# Forcer mise à jour de l’interface

# Export complet en PS
#set lalargeur "$::largeur_totale c" 
#.stateSpace.cadre.canvas postscript -file "$fichier.ps" -width $::largeur_visible -height $::hauteur_visible -x 0 -y 0 -pagewidth 1000 -colormode color
# $c postscript -file "$nomPs.ps" -height $y -width $x -pagewidth $largeur -x 0 -y 0
#.stateSpace.cadre.canvas postscript -file "$fichier.ps" -x 0 -y 0 -colormode color

# Obtenir la bounding box de tous les objets du canvas
set bbox [.stateSpace.cadre.canvas bbox all]
set x0 [expr [lindex $bbox 0] - 40]
set y0 [expr [lindex $bbox 1] - 40]
set x1 [expr [lindex $bbox 2] + 40]
set y1 [expr [lindex $bbox 3] + 40]
set width [expr {($x1 - $x0)}]
set height [expr {$y1 - $y0}]

set xview [.stateSpace.cadre.canvas xview]
set yview [.stateSpace.cadre.canvas yview]

#.stateSpace.cadre.canvas create rectangle $x0 $y0 $x1 $y1 -outline red


# Export de tout le contenu, y compris au-dessus de (0,0)
.stateSpace.cadre.canvas postscript \
    -file "$fichier.ps" \
    -x $x0 -y $y0 \
    -width $width -height $height \
    -colormode color

# Remettre la taille initiale
#.stateSpace.cadre.canvas configure -width $currentWidth -height $currentHeight

# Forcer mise à jour de l’interface
#update

    
#    .stateSpace.cadre.canvas postscript -file "$fichier.ps" -colormode color

    
    # Ouvrir le fichier avec l'application par défaut selon l'OS
if {$::plateforme eq "windows"} {
    exec start "" "$fichier.ps"
} elseif {$::osplateforme eq "Darwin"} {
#    exec pstopdf "$fichier.ps" -o "$fichier.pdf"
#    exec open "$fichier.ps" &
    if {[catch {exec which ps2pdf} ps2pdf_path] == 0} {
	exec  [exec which ps2pdf] "$fichier.ps" "$fichier.pdf"
	exec open "$fichier.pdf" &
    } elseif {[catch {exec which cupsfilter} cupsfilter_path] == 0} {
	exec  [exec which cupsfilter] "$fichier.ps" > "$fichier.pdf"
	exec open "$fichier.pdf" &
    }
} elseif {$::osplateforme eq "Linux"} {
    exec xdg-open "$fichier.ps" &
} else {
    tk_messageBox -icon error -message "Système d'exploitation non pris en charge pour l'ouverture automatique du fichier."
}

#    convert $fichier.ps $fichier.jpg
#    convert -density 150 mon_canvas.ps -quality 90 mon_canvas.jpg
}

#elseif {[string match "linux*" $tcl_platform_os]} {
 #   exec xdg-open "$fichier.ps" &
#} 
