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

# ICI
# les procedures associées aux différentes actions sur les tags :
#                   release plotDown, plotMove
# sur les places, transitions, fleches, noeuds (coudes)


# REMARQUE : le double click est dans maniTPN

# TODO TYPE   supprimerArcPlaceTransition ajouterNoeudPT ajouterNoeudPT



#*******************************************************************************************

proc majcanvas {c slave} {
global tpn projet select

set tpn(courant) [calculTPNCourant $slave]

set tpn(slave) $slave

set select(fenetre) $c

#   if {![string compare $c ".romeo.global.frame.c"]} {
#       puts "cabulanolac $c  $tpn(courant)"
#   } else {
#       puts "gna $c $tpn(courant)"
#   }
}


#*******************************************************************************************
# Les clicks sur le canvas
#*******************************************************************************************

proc directSurCanvas {w slave} {

    majcanvas $w $slave

    if {[$w find withtag current]==""} {
	return 1
    } else {
	return 0
    }
}

#*******************************---- PLOT GENERAL ----***********************************

#******************* plotDown, plotMove, posX, posY, moveX, moveY ****************


proc plotDown {w x y slave} {
    global plot
    global maxX maxY
    global select
    global zoom
    global simulatorOn
    global semExclusion

    if {($simulatorOn==0)&&($semExclusion==1)} {

	set semExclusion 0    

	
    majcanvas $w $slave
	
	set deltaX [lindex [$w xview] 0]
	set deltaY [lindex [$w yview] 0]
	set X [expr ($x/$zoom+$maxX*$deltaX/$zoom)]
	set Y [expr ($y/$zoom+$maxY*$deltaY/$zoom)]

	set plot(lastX) $X
	set plot(lastY) $Y
	set plot(downX) $X
	set plot(downY) $Y
	set select(x1) $X
	set select(x2) $X
	set select(y1) $Y
	set select(y2) $Y
	#  puts "ici $select(etat)" 

	if {$select(etat)} {
	    set select(etat) 0
	    redessinerRdP $w
	} else {
	    # reinitialiser les listes
	    set select(etat) 1

	    razListe $w 
#	    etablirListe $w [$w find enclosed $select(x1) $select(y1) $select(x2) $select(y2)]
	    set select(etat) 1
	    $w dtag selected
	    $w addtag selected withtag current
	    $w raise current

	}
	set semExclusion 1    
    } 
}

proc plotMove {w x y} {
    global plot
    global maxX maxY
    global select
    global modif 
    global tpn tabUnDo 
    global simulatorOn
    
# majcanvas $w

   if {$simulatorOn==0} {
#	modifTPN $tpn(courant)

	set select(etat) 0
	set depX [moveX $w $x]
	set depY [moveY $w $y]
	$w move selected $depX $depY
  }
}


proc posDownXY {w x y} {
    global plot
    global maxX maxY
    global zoom


    set deltaX [lindex [$w xview] 0]
    set deltaY [lindex [$w yview] 0]
    set X [expr int($x/$zoom+$maxX*$deltaX/$zoom)]
    set Y [expr int($y/$zoom+$maxY*$deltaY/$zoom)]

    set plot(lastX) $X
    set plot(lastY) $Y
    set plot(downX) $X
    set plot(downY) $Y
}



proc posX {c x} {
    global maxX
    global plot select
    global zoom

    if {$select(vide)} {
	set limG 8
	set limD 8
    } else {
	set limG  [expr {int($plot(downX) - [min $select(x1) $select(x2)])}]
	set limD  [expr {int([max $select(x1) $select(x2)] - $plot(downX))}]
    }

    set deltaX [lindex [$c xview] 0]
    set xa [expr {int($x/$zoom+$maxX*$deltaX/$zoom)}]
    if {$xa<$limG} {set xa $limG}
    if {$xa> [expr $maxX-$limD]} {set xa [expr {int($maxX-$limD)}]}
    return $xa
}


proc posY {c y} {
    global plot select
    global maxY
    global zoom

    if {$select(vide)} {
	set limH 8
	set limB 8
    } else {
	set limH  [expr  {int($plot(downY)- [min $select(y1) $select(y2)])}]
	set limB  [expr {int([max $select(y1) $select(y2)] - $plot(downY))}]
    }
    set deltaY [lindex [$c yview] 0]
    set ya [expr {int($y/$zoom+$maxY*$deltaY/$zoom)} ]
    if {$ya<$limH} {set ya $limH}
    if {$ya> [expr $maxY-$limB]} {set ya [expr {int($maxY-$limB)}] }
    return $ya
}

proc posScreenX {c x} {
    global maxX
    global zoom

    set deltaX [lindex [$c xview] 0]
    set xa [expr ($x)*$zoom]
    #     set xa [expr ($x-$maxX*$deltaX)*$zoom]
    return $xa
}
proc posScreenY {c y} {
    global maxY
    global zoom

    set deltaY [lindex [$c yview] 0]
    #     set ya [expr ($y-$maxY*$deltaY)*$zoom]
    set ya [expr ($y)*$zoom]
    return $ya
}


proc moveX {w x}  {
    global plot
    global maxX
    global select zoom

    if {$select(vide)} {
	set limG 8
	set limD 8
    } else {
	set limG  [expr $plot(downX) - [min $select(x1) $select(x2)]]
	set limD  [expr [max $select(x1) $select(x2)] - $plot(downX)]
    }

    set deltaX [lindex [$w xview] 0]
    set X [expr ($x/$zoom+$maxX*$deltaX/$zoom)]

    if {$X< $limG} {
	set X $limG
	set depX [expr $X-$plot(lastX)]
	# zoom XX
    } else {
	if {$X> [expr $maxX-$limD]} {
	    set X [expr ($maxX-$limD)]
	} else {
	    set droiteX [lindex [$w xview] 1]
	    if {$X > $maxX*$droiteX/$zoom  - 2} {
		set X [expr $X+($droiteX-$deltaX)*$maxX/(10*$zoom)]
		$w xview scroll 1 units
	    } elseif {$X < $maxX*$deltaX/$zoom + 4} {
		set X [expr $X-($droiteX-$deltaX)*$maxX/(10*$zoom)]
		$w xview scroll -1 units
	    }
	}
	set depX [expr $X-$plot(lastX)]
    }
    set plot(lastX) $X
    return [expr $depX*$zoom]
}

proc moveY {w y}  {
    global plot
    global maxY
    global select
    global zoom

    if {$select(vide)} {
	set limH 8
	set limB 8
    } else {
	set limH  [expr  $plot(downY)- [min $select(y1) $select(y2)]]
	set limB  [expr [max $select(y1) $select(y2)] - $plot(downY)]
    }

    set deltaY [lindex [$w yview] 0]
    set Y [expr ($y/$zoom+$maxY*$deltaY/$zoom)]

    if {$Y<$limH} {
	set Y $limH
    } else {
	if {$Y> [expr $maxY-$limB]} {
	    set Y [expr ($maxY-$limB)]
	} else {
	    set basY [lindex [$w yview] 1]
	    if {$Y > $maxY*$basY/$zoom - 2} {
		set Y [expr $Y+($basY-$deltaY)*$maxY/(10*$zoom)]
		$w yview scroll 1 units
	    } elseif {$Y < $maxY*$deltaY/$zoom + 4} {
		set Y [expr $Y-($basY-$deltaY)*$maxY/(10*$zoom)]
		$w yview scroll -1 units
	    }
	}
    }
    set depY [expr $Y-$plot(lastY)]
    set plot(lastY) $Y
    return [expr $depY*$zoom]
}

#***************************************************************************************
# procedure click directement sur le canvas : downSurCanvas moveSurCanvas releaseSurCanvas
#***************************************************************************************

proc moveSurCanvas {w x y} {
    global plot
    global tabPlace 
    global tabTransition
    global tpn tabUnDo
    global newFPT
    global newFTP
    global creerLien 
    global maxX maxY
    global select
    global simulatorOn 
    global creerPlace creerTransition

    if {($simulatorOn==0)&&($creerTransition>-1)&&($creerPlace>-1)} {

	if {$creerLien} {
	    creationLien $w $x $y
	} elseif {$select(etat)} {
	    creationSelection $w $x $y
	}
    } 
}

proc downSurCanvas {w a b slave} {
    global creerLien
    global creerTransition
    global creerPlace 
    global tpn tabUnDo
    global maxX
    global maxY
    global plot
    global select zoom
    global simulatorOn
    global semExclusion
    global eclair

    if {$eclair(slave)!=$slave} {
	set eclair(place)  -1
	set eclair(transition)  -1
    }
    set eclair(slave) $slave
    set deltaX [lindex [$w xview] 0]
    set deltaY [lindex [$w yview] 0]
#   set tpn(courant) [calculTPNCourant $slave]
    if {($simulatorOn==0)&&($semExclusion==1)} {
	set semExclusion 0
	majcanvas $w $slave
	if {$select(red)==0} {set select(vide) 1}
	set xa [posX $w $a]
	set ya [posY $w $b]
	if {$creerLien==1} {
	    set plot(downX) $xa
	    set plot(downY) $ya
	    set plot(lastX) $xa
	    set plot(lastY) $ya
	    creationLien $w $a $b
	} elseif {$creerTransition==1} {
	    creationTransition $w $xa $ya
	} elseif {$creerPlace==1} {
	    creationPlace $w $xa $ya
	} elseif {$creerTransition==-2} {
	    creationTransition $w $xa $ya
	    set creerPlace -2
	    set creerTransition -1
	    if {$eclair(place) > -1} {
		ajouterArcPlaceTransition  $eclair(place) $eclair(transition) 0
	    }
	} elseif {$creerPlace==-2} {
	    creationPlace $w $xa $ya
	    set creerPlace -1
	    set creerTransition -2
	    if {$eclair(transition) > -1} {
		ajouterArcTransitionPlace $eclair(transition) $eclair(place) 
	    }
	} elseif {$select(red)==0} {
	    
	    set select(tpn) $tpn(courant)
	    set select(etat) 1
	    set plot(downX) $xa
	    set plot(downY) $ya
	    set plot(lastX) $xa
	    set plot(lastY) $ya
	    set select(x1) $xa
	    set select(x2) $xa
	    set select(y1) $ya
	    set select(y2) $ya
	    $w delete fenetreSelection
	    $w dtag selected
	    razListe $w
#	    etablirListe $w [$w find enclosed $select(x1) $select(y1) $select(x2) $select(y2)]
	    redessinerRdP $w
	} 
	set semExclusion 1
     }
}

proc releaseSurCanvas {w a b} {
    global creerLien
    global creerTransition 
    global creerPlace
    global tpn tabUnDo
    global maxX
    global maxY
    global select zoom
    global simulatorOn
   global semExclusion
    
 if {($simulatorOn==0)&&($semExclusion==1)} {
     	set semExclusion 0

	if {$select(etat)&&$select(vide)&&!$creerLien} {
	    set select(etat) 0
	    #    moveX $w $a
	    #    moveY $w $b
	    # position exact
	    #zz   set select(x2) [expr [posX $w $a]*$zoom]
	    #zz   set select(y2) [expr [posY $w $b]*$zoom]
	    set select(x2) [posX $w $a]
	    set select(y2) [posY $w $b]
	    $w delete fenetreSelection
	    $w dtag selected
	    # $w addtag selected enclosed $select(x1) $select(y1) $select(x2) $select(y2)
	    set xx1 [posScreenX $w $select(x1)]
	    set xx2 [posScreenX $w $select(x2)]
	    set yy1 [posScreenY $w $select(y1)]
	    set yy2 [posScreenY $w $select(y2)]

	    if {([valabs [expr $xx1-$xx2]]<2)&&([valabs [expr $yy1-$yy2]]<2)} {
		razListe $w
	    } else {
#		etablirListe $w [$w find enclosed [posScreenX $w $select(x1)] [posScreenY $w $select(y1)] [posScreenX $w $select(x2)] [posScreenY $w $select(y2)]]
		etablirListe $w [$w find enclosed $xx1 $yy1 $xx2 $yy2]
		recreerSelected $w
		$w itemconfig selected -fill red
	    }
	} elseif {$creerLien} {
	    lienPTCree $w $a $b
	}

     set semExclusion 1
  }
}

proc valabs {a} {
    if {$a<0} {return [expr -$a]} else {return $a}
}

#*******************************---- PLOT DOWN ----***********************************

# ******************* Quand on clique *************************
# plotDown --
# Procedure appelee lorsque on clique sur l'un des cercles
# Arguments:
# w -       La fenetre canvas .
# x, y -    Les coordonnees de la souris (au moment du click).


proc clickDroitP {w x y numPlace slave} {
    global plot
    global detruirePlace
    global tabTransition  
    global tabPlace
    global tpn tabUnDo
    global destroy
    global fin
    global ok
    global newFPT
    global creerLien creerPlace
    global modif
    global select
    global simulatorOn

majcanvas $w $slave
    
    posDownXY $w $x $y
    doubleClickP $w $numPlace $slave
}

# ***************** CTRL Click sur une place *****************

proc ctrlClickP {w x y numPlace slave} {
    global plot
    global detruirePlace nbTokenColor
    global tpn tabUnDo
    global tabTransition  
    global tabPlace
    global modif
    global select
    global simulatorOn

    if {($simulatorOn==0)} {
     	set semExclusion 0
	majcanvas $w $slave
	posDownXY $w $x $y
	modifTPN $tpn(courant)
	if {$nbTokenColor($tpn(courant))==0} {
	    set tabPlace($tpn(courant),$numPlace,jeton) [expr $tabPlace($tpn(courant),$numPlace,jeton)+1]
	    redessinerRdP $w
	}
    }
 }

# *****************  Click sur une place *****************

proc plotDownP {w x y numPlace slave} {
    global plot
    global detruirePlace nbTokenColor
    global tabTransition  
    global tabPlace
    global tpn tabUnDo
    global destroy
    global fin
    global ok
    global newFPT
    global creerLien creerPlace
    global modif
    global select
    global simulatorOn
    global semExclusion
    
 if {($simulatorOn==0)&&($semExclusion==1)} {
     	set semExclusion 0

	majcanvas $w $slave
	posDownXY $w $x $y
	if {$detruirePlace == 1} {
#	    modifTPN $tpn(courant)
	    supprimerPlace $numPlace
	    redessinerRdP $w
	} elseif {$creerPlace == 2} {
	    modifTPN $tpn(courant)
	    if {$nbTokenColor($tpn(courant))==0} {
		set tabPlace($tpn(courant),$numPlace,jeton) [expr $tabPlace($tpn(courant),$numPlace,jeton)+1]
		redessinerRdP $w
	    } else {
		doubleClickP $w $numPlace $slave
	    }
	} elseif {$creerLien == 1} {
	    set xa $tabPlace($tpn(courant),$numPlace,xy,x)
	    set ya $tabPlace($tpn(courant),$numPlace,xy,y)
	    set motifFleche [$w create line $xa $ya $x $y -arrow last -tags item]
	    $w addtag newFlechePT withtag $motifFleche
	    set newFPT(place) $numPlace
	} elseif {($creerLien <6)&&($creerLien >0)} {
	    set xa $tabPlace($tpn(courant),$numPlace,xy,x)
	    set ya $tabPlace($tpn(courant),$numPlace,xy,y)
	    
	    
	    set motifCreation [$w create polygon [expr $x] [expr $y -2] \
				[expr $x -2] [expr $y] [expr $x] [expr $y + 2] \
				[expr $x + 2] [expr $y] -width 1 -outline black -fill black]  
	    set motifFleche [$w create line $xa $ya $x $y -arrow last -tags item]
	    $w addtag newFlechePTcreate withtag $motifCreation
	    $w addtag newFlechePT withtag $motifFleche
	    set newFPT(place) $numPlace
	} elseif {$select(vide)} {
	    plotDown $w $x $y $slave
	    $w dtag selected
	    $w addtag selected withtag place($numPlace)
	    $w raise current

	} elseif {![placeDansLaSelection $w $numPlace]} {
	    plotDown $w $x $y $slave
	    redessinerRdP $w
	}

	set semExclusion 1
    }
}





proc plotDownFPT {w x y numFleche slave} {
    global detruireFleche
    global tabTransition 
    global tabPlace
    global tpn tabUnDo
    global tabFlechePT
    global destroy
    global fin
    global ok
    global modif
    global creerNoeud
    global maxX
    global maxY
    global plot
    global simulatorOn
    

 majcanvas $w $slave

    if {$simulatorOn==0} {

	set T $tabFlechePT($numFleche,transition)
	set P $tabFlechePT($numFleche,place)
    set type $tabFlechePT($numFleche,type) 
 
	if {$detruireFleche == 1} {
#	    modifTPN $tpn(courant)
	    $w delete flechePT($numFleche)
	    supprimerArcPlaceTransition $P $T $type

	} elseif {$creerNoeud==1} {

#	    modifTPN $tpn(courant)
	    set xa [posX $w $x]
	    set ya [posY $w $y]
	    ajouterNoeudPT $P $T $type $xa $ya
	}
	redessinerRdP $w
    }
}



proc plotDownFTP {w x y numFleche slave} {
    global tabFlecheTP
    global detruireFleche
    global tabTransition 
    global tpn tabUnDo 
    global destroy
    global fin
    global ok
    global modif
    global creerNoeud
    global maxX
    global maxY
    global plot
    global simulatorOn
    
 majcanvas $w $slave

    if {$simulatorOn==0} {
	
	set T $tabFlecheTP($numFleche,transition)
	set P $tabFlecheTP($numFleche,place)

	# ajouter un noeud dans les arxs ++++++++++++
	if {$creerNoeud==1} {
#	    modifTPN $tpn(courant)
	    set xa [posX $w $x]
	    set ya [posY $w $y]
	    ajouterNoeudTP $T $P $xa $ya

	} elseif {$detruireFleche == 1} {

	    $w delete flecheTP($numFleche)
#	    modifTPN $tpn(courant)
	    supprimerArcTransitionPlace $T $P
	}
	redessinerRdP $w
    }
}



# ***************** Click sur un Weight (et inhibitor condition *****************

proc plotDownWeight {w x y numFleche slave} {
    global detruireFleche
    global tabTransition 
    global tabPlace
    global tpn tabUnDo
    global tabFlechePT
    global destroy
    global fin
    global ok
    global modif
    global creerNoeud
    global maxX
    global maxY
    global plot select
    global simulatorOn

 majcanvas $w $slave
    
    if {$simulatorOn==0} {

	set T $tabFlechePT($numFleche,transition)
	set P $tabFlechePT($numFleche,place)
    set type $tabFlechePT($numFleche,type) 
 
	posDownXY $w $x $y

	if {$detruireFleche == 1} {
#	    modifTPN $tpn(courant)
	    $w delete flechePT($numFleche)
	    supprimerArcPlaceTransition $P $T $type

	} elseif {$select(vide)} {

	    plotDown $w $x $y $slave

	} elseif {$creerNoeud==1} {

#	    modifTPN $tpn(courant)
	    set xa [posX $w $x]
	    set ya [posY $w $y]
	    ajouterNoeudPT $P $T $type $xa $ya
	}
    }
}

# ***************** Click sur un noeud *****************

proc plotDownNoeud {w x y numNoeud slave} {
    global detruireNoeud
    global tabTransition 
    global tabPlace
    global tpn tabUnDo
    global tabNoeud
    global destroy
    global fin
    global ok
    global creerLien
    global modif
    global plot
    global maxX maxY
    global select

    global simulatorOn

 majcanvas $w $slave
    
    if {$simulatorOn==0} {


	posDownXY $w $x $y

	if {$detruireNoeud==1} {
	    modifTPN $tpn(courant)
	    supprimerNoeud $numNoeud
	    redessinerRdP $w
	} elseif {$select(vide)} {
	    plotDown $w $x $y $slave
	} elseif {![noeudDansLaSelection $w $numNoeud]} {
	    plotDown $w $x $y $slave
	    redessinerRdP $w
	}
    }
}




proc plotDownLabelPlace {w x y numPlace slave} {
    global plot
    global tabPlace 
    global tpn tabUnDo
    global destroy
    global fin
    global ok
    global modif
    global select
    global simulatorOn

 majcanvas $w $slave
    
    if {$simulatorOn==0} {
#	modifTPN $tpn(courant)
	posDownXY $w $x $y
	if {$select(vide)} {
	    plotDown $w $x $y $slave
	} elseif {![labelPlaceDansLaSelection $w $numPlace]} {
	    plotDown $w $x $y $slave
	    redessinerRdP $w
	}
    }
}

proc plotDownLabelTransition {w x y numTransition slave} {
    global plot
    global tabPlace 
    global tpn tabUnDo 
    global destroy
    global fin
    global ok
    global modif
    global select
    global simulatorOn

 majcanvas $w $slave
    
    if {$simulatorOn==0} {
#	modifTPN $tpn(courant)
	
	posDownXY $w $x $y
	if {$select(vide)} {
	    plotDown $w $x $y $slave
	} elseif {![labelTransitionDansLaSelection $w $numTransition]} {
	    plotDown $w $x $y $slave
	    redessinerRdP $w
	}
    }
}

proc plotDownGuardTransition {w x y numTransition slave} {
    global plot
    global tabPlace 
    global tpn tabUnDo 
    global destroy
    global fin
    global ok
    global modif
    global select
    global simulatorOn

 majcanvas $w $slave
    
    if {$simulatorOn==0} {
	
	posDownXY $w $x $y
	if {$select(vide)} {
	    plotDown $w $x $y $slave
	}
    }
}

proc plotDownUpdateTransition {w x y numTransition slave} {
    global plot
    global tabPlace 
    global tpn tabUnDo 
    global destroy
    global fin
    global ok
    global modif
    global select
    global simulatorOn

 majcanvas $w $slave
    
    if {$simulatorOn==0} {
	
	posDownXY $w $x $y
	if {$select(vide)} {
	    plotDown $w $x $y $slave
	}
    }
}

proc plotDownSpeedTransition {w x y numTransition slave} {
    global plot
    global tabPlace 
    global tpn tabUnDo 
    global destroy
    global fin
    global ok
    global modif
    global select
    global simulatorOn

 majcanvas $w $slave
    
    if {$simulatorOn==0} {
	
	posDownXY $w $x $y
	if {$select(vide)} {
	    plotDown $w $x $y $slave
	}
    }
}


proc plotDownCostTransition {w x y numTransition slave} {
    global plot
    global tabPlace 
    global tpn tabUnDo 
    global destroy
    global fin
    global ok
    global modif
    global select
    global simulatorOn

 majcanvas $w $slave
    
    if {$simulatorOn==0} {
	
	posDownXY $w $x $y
	if {$select(vide)} {
	    plotDown $w $x $y $slave
	}
    }
}


proc plotDownT {w x y numTransition slave} {
    global plot
    global detruireTransition
    global tabTransition 
    global tpn tabUnDo 
    global destroy
    global creerLien
    global newFTP
    global modif
    global select
    global simulatorOn
    global firingSequence 

 majcanvas $w $slave
    
    if {$simulatorOn==1} {
	simulatorFireTranstion $w $numTransition $slave
    } else {
#	modifTPN $tpn(courant)

	posDownXY $w $x $y

	if {$detruireTransition == 1} {
	    supprimerTransition  $numTransition
	    redessinerRdP $w
	} elseif {$creerLien == 1} {               # ***************** SEULEMENT POUR LES ARCS CLASSIQUES
	    set xa $tabTransition($tpn(courant),$numTransition,xy,x)
	    set ya $tabTransition($tpn(courant),$numTransition,xy,y)

	    set motifFleche [$w create line $xa $ya $x $y -arrow last -tags item]
	    $w addtag newFlecheTP withtag $motifFleche
	    set newFTP(transition) $numTransition

	} elseif {$select(vide)} {
	    plotDown $w $x $y $slave
	} elseif {![transitionDansLaSelection $w $numTransition]} {
	    plotDown $w $x $y $slave
	    redessinerRdP $w
	}    
    }
}

#**************** CLICK DROIT*******************


proc clickDroitFTP {w x y numFleche slave} {
    global detruireFleche
    global tabTransition
    global tabPlace 
    global tpn tabUnDo 
    global tabFlecheTP
    global modif
    global maxX
    global maxY
    global plot zoom
    global simulatorOn

 majcanvas $w $slave

    if {$simulatorOn==0} {
	set T $tabFlecheTP($numFleche,transition)
	set P $tabFlecheTP($numFleche,place)
	modifTPN $tpn(courant)
	set xa [posX $w $x]
	set ya [posY $w $y]
	ajouterNoeudTP $T $P $xa $ya
	redessinerRdP $w
    }
}

proc clickDroitFPT {w x y numFleche slave} {
    global detruireFleche
    global tabTransition  
    global tabPlace
    global tpn tabUnDo
    global tabFlechePT
    global modif
    global maxX
    global maxY
    global plot
    global simulatorOn

 majcanvas $w $slave

   if {$simulatorOn==0} {
       set T $tabFlechePT($numFleche,transition)
       set P $tabFlechePT($numFleche,place)
       set type $tabFlechePT($numFleche,type) 
       modifTPN $tpn(courant)
       set xa [posX $w $x]
       set ya [posY $w $y]
       ajouterNoeudPT $P $T $type $xa $ya
       redessinerRdP $w
   }
}


proc clickDroitSurCanvas {c x y slave} {
    global select
    global simulatorOn

 set onsupprime 1
    if {$onsupprime==0} {
    majcanvas $c $slave
    if {($select(red)==0)&&($simulatorOn==0)} {
	destroy $c.add
	menu $c.add -tearoff 0
	$c.add add command -label [mc "Place"] -command "clickNewPlace $c.add $c $x $y"
	$c.add add command -label [mc "Transition"] -command "clickNewTransition $c.add $c $x $y"
	tk_popup $c.add [expr $x+[winfo rootx $c]] [expr $y+[winfo rooty $c]] 0
    }
 }
}

proc clickNewPlace {m c x y} {
    global simulatorOn
   if {$simulatorOn==0} {
       creationPlace $c [posX $c $x] [posY $c $y]
       destroy $m
   }
}

proc clickNewTransition {m c x y} {
    global simulatorOn

   if {$simulatorOn==0} {
       creationTransition $c [posX $c $x] [posY $c $y]
       destroy $m
   }
}




#*******************************************************************************************
# Any enter et Anyleave
#*******************************************************************************************

proc anyLeaveArc {c color} {
    global select
    global simulatorOn
    global tabColor
    
    if {$simulatorOn==0} {
	set select(red) 0
	$c itemconfig current -fill $tabColor(Arc,$color)
    }   
}


proc anyLeaveWeight {c} {
    global select

    set select(red) 0
    $c itemconfig current -fill green4
}


proc anyEnter {c} {
    global select
    global simulatorOn
    if {$simulatorOn==0} {
	set select(red) 1
	$c itemconfig current -fill red
    }
}

proc anyEnterTransition {c i} {
    global select
    global simulatorOn
    set select(red) 1
    if {$simulatorOn==1} {

	set slave [retrouverMasterSlaveFromCanvas $c]
	set underscore "_"
	if {[firable $slave$underscore$i]==1} {$c itemconfig current -fill red}
    } else {
	$c itemconfig current -fill red
    }  
}

proc anyEnterPlace {c i} {
    global select
    global simulatorOn
    if {$simulatorOn==0} {
	set select(red) 1
	$c itemconfig place($i) -fill red
	#  $c lower place($i) jet($i)
	
    }
}


proc anyLeavePlace {c i initialcolor} {
    global select
    global tabPlace 
    global tpn tabUnDo
    global simulatorOn
    global tabColor
    
    set select(red) 0
    if {$simulatorOn==0} {
	if {![placeDansLaSelection $c $i]} {
	    $c itemconfig place($i) -fill $initialcolor
	}
    }
}

proc anyLeaveNoeud {c i} {
    global select
    global simulatorOn
    global tabColor

    set select(red) 0
    if {$simulatorOn==0} {
	if {![noeudDansLaSelection $c $i]} {
	    $c itemconfig current -fill green
	}
    } 
}

proc anyLeaveLabelPlace {c i} {
    global select

    set select(red) 0
    if {![labelPlaceDansLaSelection $c $i]} {
	$c itemconfig current -fill blue4
    }
}

proc anyLeaveTransition {c i initialcolor} {
    global select
    global simulatorOn
    global tabTransition tabColor tpn

    set select(red) 0
    $c itemconfig current -fill $initialcolor
    #if {$simulatorOn==1} {
#	if {[firable $i]==1} {set laCouleur $tabColor(simulator,firableTrans)
#	} elseif {[enabled $i]==1} {set laCouleur $tabColor(simulator,enabledTrans)
#	} else {set laCouleur $tabColor(simulator,noEnabledTrans)}
#	$c itemconfig current -fill $initialcolor
 #   } else {
#	if {![transitionDansLaSelection $c $i]} {
#	    $c itemconfig current -fill $initialcolor
#	}
 #   } 
}

proc anyLeaveLabelTransition {c i} {
    global select

    set select(red) 0
    if {![labelTransitionDansLaSelection $c $i]} {
	$c itemconfig current -fill darkgoldenrod4
    }
}

proc anyLeaveGuardTransition {c i} {
    global select

    set select(red) 0
    if {![labelTransitionDansLaSelection $c $i]} {
	$c itemconfig current -fill darkgreen
    }
}

proc anyLeaveUpdateTransition {c i} {
    global select

    set select(red) 0
    if {![labelTransitionDansLaSelection $c $i]} {
	$c itemconfig current -fill blue
    }
}

proc anyLeaveSpeedTransition {c i} {
    global select

    set select(red) 0
    if {![labelTransitionDansLaSelection $c $i]} {
	$c itemconfig current -fill DarkOrchid4
    }
}

proc anyLeaveCostTransition {c i} {
    global select

    set select(red) 0
    if {![labelTransitionDansLaSelection $c $i]} {
	$c itemconfig current -fill VioletRed4
    }
}


#*******************************----deplacementSignificatif ----***********************************

proc deplacementSignificatif {c x y} {
  global plot

    set depEnX [expr [posX $c $x] - $plot(downX)]
    set depEnY [expr [posY $c $y] - $plot(downY)]
    if {($depEnX >= 1) || ($depEnX <=-1) || ($depEnY >= 1) || ($depEnY <= -1)} {
	return 1
    } else {
	return 0
    }
}


#*******************************---- PLOT RELEASE ----***********************************
#******************************* Util pour le Dessin des arcs ----***********************************

#+++++++++++++++ validation quand on relache le bouton de la souris


proc releaseWeight {c x y numTrans} {
    global tabTransition 
    global tpn tabUnDo
    global fin
    global plot
    global modif
    global maxX maxY zoom
    global simulatorOn semaphore

    if {$simulatorOn==0} { 
	if {$semaphore(Release)==1} { 

	    if {[deplacementSignificatif $c $x $y]==1} {
		set dxa [expr [posX $c $x] - $plot(downX)]
		set dya [expr [posY $c $y] - $plot(downY)]
		modifTPN $tpn(courant)
		modifPositionWeightInhibCond $dxa $dya [posX $c $x]  [posY $c $y] $numTrans
	    }
	    redessinerRdP $c
	}  elseif {$semaphore(Release)==0} {
	      set semaphore(Release) 1
	}
    }
}


proc releaseNoeud {c x y numNoeud} {
    global tabTransition 
    global tpn tabUnDo
    global fin
    global plot
    global modif
    global maxX maxY zoom
    global simulatorOn

    if {$simulatorOn==0} {  
	set xa [expr [posX $c $x]]
	set ya [expr [posY $c $y]]

	if {[noeudDansLaSelection $c $numNoeud]} {
	    deplacerLaSelection $c $x $y
	} else {
	    modifTPN $tpn(courant)
	    modifRelativePositionNoeud  [expr [posX $c $x] - $plot(downX)] [expr [posY $c $y] - $plot(downY)] $numNoeud
	    redessinerRdP $c
	}}
}


proc posSurGrille {x} {
global grille

    set mulgrille [expr 15.0*$grille]
    if {$mulgrille==0} {set mulgrille 1}
    set resultat [expr round(($x-1.0)/($mulgrille))*$mulgrille +1 ]
    if {$resultat<1} {set  resultat 1}
    return $resultat
}

proc releasePlace {c x y i} {
    global plot
    global tabPlace 
    global tpn tabUnDo
    global maxX
    global maxY
    global select modif
    global creerLien
    global zoom
    global simulatorOn
    global semaphore 


    if {$simulatorOn==0} {  

	if {$creerLien} {
	} elseif {[placeDansLaSelection $c $i]} {
	    deplacerLaSelection $c $x $y
	} elseif {$semaphore(Release)==1} {
	    if {[deplacementSignificatif $c $x $y]==1} {
		set xrelease [posSurGrille [expr $tabPlace($tpn(courant),$i,xy,x) + [posX $c $x] - $plot(downX)]]
		set yrelease [posSurGrille [expr $tabPlace($tpn(courant),$i,xy,y) + [posY $c $y] - $plot(downY)]]
		modifTPN $tpn(courant)
		set tabPlace($tpn(courant),$i,xy,x) $xrelease
		set tabPlace($tpn(courant),$i,xy,y) $yrelease
		redessinerRdP $c
	    }
	}  elseif {$semaphore(Release)==0} {
	      set semaphore(Release) 1
	}
   }
}

proc releaseLabelPlace {c x y i} {
    global plot
    global tabPlace 
    global tpn tabUnDo 
    global maxX
    global maxY
    global select zoom modif 
    global simulatorOn semaphore

    if {$simulatorOn==0} {  
      if {$semaphore(Release)==1} { 
	if {[labelPlaceDansLaSelection $c $i]} {
	    deplacerLaSelection $c $x $y
	} elseif {[deplacementSignificatif $c $x $y]==1} {

	    set xrelease [expr $tabPlace($tpn(courant),$i,label,dx) + [posX $c $x] - $plot(downX)]
	    set yrelease [expr $tabPlace($tpn(courant),$i,label,dy) + [posY $c $y] - $plot(downY)]
	    modifTPN $tpn(courant)
	    set tabPlace($tpn(courant),$i,label,dx) $xrelease
	    set tabPlace($tpn(courant),$i,label,dy) $yrelease
	    redessinerRdP $c
	} 
      }  else {   # cad  $semaphore(Release)==0
	      set semaphore(Release) 1
	}
    }
}

proc releaseTransition {c x y i} {
    global semaphore 
    global plot
    global tabTransition 
    global tpn tabUnDo 
    global maxX
    global maxY
    global select
    global creerLien
    global zoom modif
    global simulatorOn

    if {$simulatorOn==0} {  

	if {$creerLien} {
	} elseif {[transitionDansLaSelection $c $i]} {
	    deplacerLaSelection $c $x $y
	} elseif {$semaphore(Release)==1} {
	    if {[deplacementSignificatif $c $x $y]==1} {
		set xrelease [posSurGrille [expr $tabTransition($tpn(courant),$i,xy,x) + [posX $c $x] - $plot(downX)]]
		set yrelease [posSurGrille [expr $tabTransition($tpn(courant),$i,xy,y) + [posY $c $y] - $plot(downY)]]
		modifTPN $tpn(courant)
		set tabTransition($tpn(courant),$i,xy,x) $xrelease
		set tabTransition($tpn(courant),$i,xy,y) $yrelease
		redessinerRdP $c
	    }
	}  elseif {$semaphore(Release)==0} {
	      set semaphore(Release) 1
	}
   }
}

proc releaseLabelTransition {c x y i} {
    global plot
    global tabTransition 
    global tpn tabUnDo 
    global maxX
    global maxY
    global select zoom modif
    global simulatorOn semaphore

    if {$simulatorOn==0} {  
      if {$semaphore(Release)==1} { 
	if {[labelTransitionDansLaSelection $c $i]} {
	    deplacerLaSelection $c $x $y
	} elseif {[deplacementSignificatif $c $x $y]==1} {
	    set xdiff [expr [posX $c $x] - $plot(downX)]
	    set ydiff [expr [posY $c $y] - $plot(downY)]
	    modifTPN $tpn(courant)
	    set tabTransition($tpn(courant),$i,label,dx) [expr $tabTransition($tpn(courant),$i,label,dx) + [posX $c $x] - $plot(downX)]
	    set tabTransition($tpn(courant),$i,label,dy) [expr $tabTransition($tpn(courant),$i,label,dy) + [posY $c $y] - $plot(downY)]
	    redessinerRdP $c
	}
       }  else {   # cad  $semaphore(Release)==0
	      set semaphore(Release) 1
       }
    }
}


proc releaseGuardTransition {c x y i} {
    global plot
    global tabTransition 
    global tpn tabUnDo 
    global maxX
    global maxY
    global select zoom modif
    global simulatorOn semaphore

    if {$simulatorOn==0} {  
      if {$semaphore(Release)==1} { 
	if {[deplacementSignificatif $c $x $y]==1} {
	    set xdiff [expr [posX $c $x] - $plot(downX)]
	    set ydiff [expr [posY $c $y] - $plot(downY)]
	    modifTPN $tpn(courant)
	    set tabTransition($tpn(courant),$i,guard,dx) [expr $tabTransition($tpn(courant),$i,guard,dx) + [posX $c $x] - $plot(downX)]
	    set tabTransition($tpn(courant),$i,guard,dy) [expr $tabTransition($tpn(courant),$i,guard,dy) + [posY $c $y] - $plot(downY)]
	    redessinerRdP $c
	}
      }  else {   # cad  $semaphore(Release)==0
	      set semaphore(Release) 1
      }
    }   
}

proc releaseUpdateTransition {c x y i} {
    global plot
    global tabTransition 
    global tpn tabUnDo 
    global maxX
    global maxY
    global select zoom modif
    global simulatorOn semaphore

    if {$simulatorOn==0} {  
      if {$semaphore(Release)==1} { 
	if {[deplacementSignificatif $c $x $y]==1} {
	    set xdiff [expr [posX $c $x] - $plot(downX)]
	    set ydiff [expr [posY $c $y] - $plot(downY)]
	    modifTPN $tpn(courant)
	    set tabTransition($tpn(courant),$i,update,dx) [expr $tabTransition($tpn(courant),$i,update,dx) + [posX $c $x] - $plot(downX)]
	    set tabTransition($tpn(courant),$i,update,dy) [expr $tabTransition($tpn(courant),$i,update,dy) + [posY $c $y] - $plot(downY)]
	    redessinerRdP $c
	}
      }
  }  else {   # cad  $semaphore(Release)==0
      set semaphore(Release) 1
  }   
}

proc releaseSpeedTransition {c x y i} {
    global plot
    global tabTransition 
    global tpn tabUnDo 
    global maxX
    global maxY
    global select zoom modif
    global simulatorOn semaphore

    if {$simulatorOn==0} {  
      if {$semaphore(Release)==1} { 
	if {[deplacementSignificatif $c $x $y]==1} {	
	    set xdiff [expr [posX $c $x] - $plot(downX)]
	    set ydiff [expr [posY $c $y] - $plot(downY)]
	    modifTPN $tpn(courant)
	    set tabTransition($tpn(courant),$i,speed,dx) [expr $tabTransition($tpn(courant),$i,speed,dx) + [posX $c $x] - $plot(downX)]
	    set tabTransition($tpn(courant),$i,speed,dy) [expr $tabTransition($tpn(courant),$i,speed,dy) + [posY $c $y] - $plot(downY)]
	    redessinerRdP $c
	}
      }  else {   # cad  $semaphore(Release)==0
	  set semaphore(Release) 1
      }
    }   
}

proc releaseCostTransition {c x y i} {
    global plot
    global tabTransition 
    global tpn tabUnDo 
    global maxX
    global maxY
    global select zoom modif
    global simulatorOn semaphore

    if {$simulatorOn==0} {  
      if {$semaphore(Release)==1} { 
	if {[deplacementSignificatif $c $x $y]==1} {
	    set xdiff [expr [posX $c $x] - $plot(downX)]
	    set ydiff [expr [posY $c $y] - $plot(downY)]
	    modifTPN $tpn(courant)
	    set tabTransition($tpn(courant),$i,cost,dx) [expr $tabTransition($tpn(courant),$i,cost,dx) + [posX $c $x] - $plot(downX)]
	    set tabTransition($tpn(courant),$i,cost,dy) [expr $tabTransition($tpn(courant),$i,cost,dy) + [posY $c $y] - $plot(downY)]
	    redessinerRdP $c
	}
      }  else {   # cad  $semaphore(Release)==0
	  set semaphore(Release) 1
      } 
    }   
}

#*******************************---- PLOT MOVE ----***********************************

# ******************** Quand on bouge la souris ***************************
# plotMove --
# Procedure invoquee pendant le deplacement de la souris (avec selection
# d'un cercle  Elle deplace l'item courant
#
# Arguments:
# w -       La fenetre canvas.
# x, y -    Les coordonnees de la souris.

proc plotMoveNoeud {w x y indice}  {
    global plot
    global maxX maxY
    global modif
    global select
    global simulatorOn
    
    if {$simulatorOn==0} {
	plotMove $w $x $y
    }
}

proc plotMoveWeight {w x y indice}  {
    global plot
    global maxX maxY
    global modif
    global select
    global simulatorOn
    
    if {$simulatorOn==0} {
	plotMove $w $x $y
    }
}

proc plotMoveTransition {w x y i} {
    global plot
    global creerLien
    global modif
    global maxX maxY
    global select
    global simulatorOn
    
    if {$simulatorOn==0} {
	if {$creerLien == 0}  {
	    plotMove $w $x $y
	}
    } 
}


proc plotMovePlace {w x y i} {
    global plot
    global modif 
    global tpn tabUnDo
    global creerLien
    global maxX maxY
    global select
    global simulatorOn
    
    if {$simulatorOn==0} {
	if {$creerLien == 0}  {
	    plotMove $w $x $y
	}}
}

proc plotMoveLabelTransition {w x y i} {
    global plot
    global modif
    global maxX maxY
    global select
    global simulatorOn
    
    if {$simulatorOn==0} {
	plotMove $w $x $y
    }
}

proc plotMoveGuardTransition {w x y i} {
    global plot
    global modif
    global maxX maxY
    global select
    global simulatorOn
    
    if {$simulatorOn==0} {
	plotMove $w $x $y
    }
}

proc plotMoveUpdateTransition {w x y i} {
    global plot
    global modif
    global maxX maxY
    global select
    global simulatorOn
    
    if {$simulatorOn==0} {
	plotMove $w $x $y
    }
}

proc plotMoveSpeedTransition {w x y i} {
    global plot
    global modif
    global maxX maxY
    global select
    global simulatorOn
    
    if {$simulatorOn==0} {
	plotMove $w $x $y
    }
}


proc plotMoveCostTransition {w x y i} {
    global plot
    global modif
    global maxX maxY
    global select
    global simulatorOn
    
    if {$simulatorOn==0} {
	plotMove $w $x $y
    }
}

proc plotMoveLabelPlace {w x y i} {
    global plot
    global modif
    global max maxY
    global select
    global simulatorOn
    
    if {$simulatorOn==0} {
	plotMove $w $x $y
    }
}


#*******************************---- CREATION DES ARCS (lien) ----***********************************


proc creationLien {w x y} {
    global plot
    global tabPlace 
    global tabTransition
    global tpn tabUnDo
    global newFPT
    global newFTP
    global creerLien
    global maxX maxY zoom
    global simulatorOn
    # scrolling
    moveX $w $x
    moveY $w $y

    # position exact
    set x [posX $w $x]
    set y [posY $w $y]

    if {$creerLien==1} {

	  if {$newFPT(place)>0 } {

	    $w delete newFlechePT
	    set xa $tabPlace($tpn(courant),$newFPT(place),xy,x)
	    set ya $tabPlace($tpn(courant),$newFPT(place),xy,y)

	    set motifFleche [$w create line $xa $ya $x $y -arrow last -tags item]
	    $w addtag newFlechePT withtag $motifFleche
	    set plot(lastX) $x
	    set plot(lastY) $y
	    $w scale newFlechePT 0 0 $zoom $zoom

	  } elseif {$newFTP(transition)>0 } {

	    $w delete newFlecheTP
	    set xa $tabTransition($tpn(courant),$newFTP(transition),xy,x)
	    set ya $tabTransition($tpn(courant),$newFTP(transition),xy,y)

	    set motifFleche [$w create line $xa $ya $x $y -arrow last -tags item]
	    $w addtag newFlecheTP withtag $motifFleche
	    $w scale newFlecheTP 0 0 $zoom $zoom
	    #    set plot(lastX) $x
	    #    set plot(lastY) $y
	  }
	# si creation d'arc flush ou read ou inhibitor :
    } else {
	if {$newFPT(place)>0 } {

	    $w delete newFlechePT
	    $w delete newFlechePflush
	    set xa $tabPlace($tpn(courant),$newFPT(place),xy,x)
	    set ya $tabPlace($tpn(courant),$newFPT(place),xy,y)
	    set motifFlush [$w create polygon [expr $x] [expr $y -3] \
				[expr $x -3] [expr $y] [expr $x] [expr $y + 3] \
				[expr $x + 3] [expr $y] -width 1 -outline black -fill black]  
	    set motifFleche [$w create line $xa $ya $x $y -tags item]
	    $w addtag newFlechePflush withtag $motifFlush
	    $w addtag newFlechePT withtag $motifFleche
	    set plot(lastX) $x
	    set plot(lastY) $y
	    $w scale newFlechePflush 0 0 $zoom $zoom
	    $w scale newFlechePT 0 0 $zoom $zoom

	} 
	
    }
}


proc lienPTCree {c x y} {
    global tabTransition
    global tabPlace 
    global tpn tabUnDo
    global newFPT
    global newFTP
    global fin
    global ok
    global creerLien
    global modif
    global maxX
    global maxY zoom
    global simulatorOn


  set x [posX $c $x]
  set y [posY $c $y]

  if {$simulatorOn==0} {
    if {[expr $creerLien * $newFPT(place)]>0 } {
	set lePlusProche 1000
	set distance 1000

	for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {

	    if {$tabTransition($tpn(courant),$i,statut) == $ok} {
		set x2 $tabTransition($tpn(courant),$i,xy,x)
		set y2 $tabTransition($tpn(courant),$i,xy,y)
		set distance [expr ($x-$x2)*($x-$x2)+($y-$y2)*($y-$y2)]
		if {$distance < $lePlusProche} {
		    set lePlusProche $distance
		    set laTransition $i
		}
	    }
	}
	if {$lePlusProche < 1000} {
	    modifTPN $tpn(courant)
	    ajouterArcPlaceTransition $newFPT(place) $laTransition [expr $creerLien -1]
	}
	set newFPT(place) 0

    }  elseif {[expr $creerLien * $newFTP(transition) ] >= 1 } {

	set lePlusProche 1000
	set distance 1000

	for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin}  {incr i} {

	    if {$tabPlace($tpn(courant),$i,statut) == $ok} {
		set x2 $tabPlace($tpn(courant),$i,xy,x)
		set y2 $tabPlace($tpn(courant),$i,xy,y)
		set distance [expr ($x-$x2)*($x-$x2)+($y-$y2)*($y-$y2)]
		if {$distance < $lePlusProche} {
		    set lePlusProche $distance
		    set laPlace $i
		}
	    }
	}
	if {$lePlusProche < 1000} {
	    modifTPN $tpn(courant)
	    ajouterArcTransitionPlace $newFTP(transition) $laPlace
	}
	set newFTP(transition) 0
    }
    redessinerRdP $c
  }
    set plot(lastX) $x
    set plot(lastY) $y
  
}

#****************************************************************************************************
#****************************** SELECTIONNER COPIER DEPLACER COLLER *********************************
#****************************************************************************************************

#*******************************---- CREATION DES ARCS (lien) ----***********************************


proc creationSelection {w x y} {
    global plot
    global tabPlace 
    global tabTransition
    global tpn tabUnDo
    global newFPT
    global newFTP
    global creerLien
    global maxX maxY
    global select zoom
    global simulatorOn
    
    if {$simulatorOn==0} {
	# scrolling
	if {$select(etat)&&!$creerLien} {
	    moveX $w $x
	    moveY $w $y
	    # position exact
	    
	    set select(x2) [posX $w $x]
	    set select(y2) [posY $w $y]

	    $w delete fenetreSelection
	    #     set motifSelection [$w create rect $select(x1) $select(y1) $select(x2) $select(y2) -width 1 -outline black]
	    set motifSelection [$w create rect [posScreenX $w $select(x1)] [posScreenY $w $select(y1)] [posScreenX $w $select(x2)] [posScreenY $w $select(y2)] -width 1 -outline black]
	    $w addtag fenetreSelection withtag $motifSelection
	    #     $w scale fenetreSelection 0 0 $zoom $zoom 
	}}
}



proc placeDansLaSelection {w laPlace} {
    global select
    if {[lsearch $select(listePlace) $laPlace]!=-1} {
	return 1
    } else {
	return 0
    }
}

proc labelPlaceDansLaSelection {w labelPlace} {
    global select
    if {[lsearch $select(listeLabelPlace) $labelPlace]!=-1} {
	return 1
    } else {
	return 0
    }
}

proc noeudDansLaSelection {w leNoeud} {
    global select
    if {[lsearch $select(listeNoeud) $leNoeud]!=-1} {
	return 1
    } else {
	return 0
    }
}


proc transitionDansLaSelection {w laTransition} {
    global select
    if {[lsearch $select(listeTransition) $laTransition]!=-1} {
	return 1
    } else {
	return 0
    }
}

proc labelTransitionDansLaSelection {w labelTransition} {
    global select
    if {[lsearch $select(listeLabelTransition) $labelTransition]!=-1} {
	return 1
    } else {
	return 0
    }
}

#++++++++++++++++++++++indice dans tabNoeud

proc indiceNoeudPT {P T type} {
    global tabTransition 
    global tpn tabUnDo
    global tabFlechePT tabFlecheTP tabNoeud

    for {set k 1} {$tabFlechePT($k,transition)>-1} {incr k} {
	if {($tabFlechePT($k,transition)==$T)&&($tabFlechePT($k,place)==$P)&&($tabFlechePT($k,type)==$type)} {
	    for {set kprim 1} {$tabNoeud($kprim,arc)>-1} {incr kprim} {
		if {($tabNoeud($kprim,TP)==-1)&&($tabNoeud($kprim,arc)==$k)} {
		    return $kprim
		}
	    }
	}
    }
    return -1
}

proc indiceNoeudTP {T P} {
    global tabTransition 
    global tpn tabUnDo
    global tabFlecheTP tabNoeud

    for {set k 1} {$tabFlecheTP($k,transition)>-1} {incr k} {
	if {($tabFlecheTP($k,transition)==$T)&&($tabFlecheTP($k,place)==$P)} {
	    for {set kprim 1} {$tabNoeud($kprim,arc)>-1} {incr kprim} {
		if {($tabNoeud($kprim,TP)==1)&&($tabNoeud($kprim,arc)==$k)} {
		    return $kprim
		}
	    }
	}
    }
    return -1
}

#++++++++++++++++++++++ Copier coller +++++++++++++++++++++++
proc razListe {c} {
    global tabPlace  
    global tabTransition tabNoeud
    global tpn tabUnDo
    global fin
    global ok
    global destroy
    global plot
    global select

    set select(tpn) 0
    set select(vide) 1
    set select(listePlace) [list]
    set select(listeLabelPlace) [list]
    set select(listeTransition) [list]
    set select(listeLabelTransition) [list]
    set select(listeNoeud) [list]

}

proc etablirListe {c liste} {
    global tabPlace  
    global tabTransition tabNoeud
    global tpn tabUnDo
    global fin
    global ok
    global destroy
    global plot
    global select


    set select(tpn) $tpn(courant)
    set select(onglet) $tpn(onglet)
    set select(vide) 1
    set select(listePlace) [list]
    set select(listeLabelPlace) [list]
    set select(listeTransition) [list]
    set select(listeLabelTransition) [list]
    set select(listeNoeud) [list]



    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
	if {$tabPlace($tpn(courant),$i,statut)==$ok} {
	    set element [$c find withtag place($i)]
	    if {[lsearch $liste $element]!=-1} {
		lappend select(listePlace) $i
		set select(vide) 0
	    }
	    set element [$c find withtag labelPlace($i)]
	    if {[lsearch $liste $element]!=-1} {
		lappend select(listeLabelPlace) $i
		set select(vide) 0
	    }
	}
    }
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
	if {$tabTransition($tpn(courant),$i,statut) == $ok} {
	    set element [$c find withtag transition($i)]
	    if {[lsearch $liste $element]!=-1} {
		lappend select(listeTransition) $i
		set select(vide) 0
	    }
	    set element [$c find withtag labelTransition($i)]
	    if {[lsearch $liste $element]!=-1} {
		lappend select(listeLabelTransition) $i
		set select(vide) 0
	    }
	}
    }
    for {set i 1} {$tabNoeud($i,arc)>0} {incr i} {
	set element [$c find withtag noeud($i)]
	if {[lsearch $liste $element]!=-1} {
	    lappend select(listeNoeud) $i
	    set select(vide) 0
	}
    }
}

proc recreerSelected {c} {
    global tabPlace  
    global tabTransition tabNoeud
    global tpn tabUnDo
    global fin
    global ok
    global destroy
    global plot
    global select

    $select(fenetre) dtag selected
    set select(fenetre) $c
    for {set i 0} {$i<[llength $select(listePlace)]} {incr i} {
	$c addtag selected withtag place([lindex $select(listePlace) $i])
	$c addtag selected withtag labelPlace([lindex $select(listePlace) $i])
    }
    for {set i 0} {$i<[llength $select(listeNoeud)]} {incr i} {
	$c addtag selected withtag noeud([lindex $select(listeNoeud) $i])
    }
    for {set i 0} {$i<[llength $select(listeTransition)]} {incr i} {
	$c addtag selected withtag transition([lindex $select(listeTransition) $i])
	$c addtag selected withtag labelTransition([lindex $select(listeTransition) $i])
    }
}

proc deplacerLaSelection {c x y} {
    global tabPlace 
    global tabTransition
    global tpn tabUnDo
    global fin
    global ok
    global destroy modif
    global plot
    global select
    global simulatorOn

  if {$simulatorOn==0} {
    if  {$select(tpn) == $tpn(courant)}    {
	modifTPN $tpn(courant)

	set depX [expr [posX $c $x] - $plot(downX)]
	set depY [expr [posY $c $y] - $plot(downY)]
	set select(x1) [expr $select(x1) + $depX]
	set select(x2) [expr $select(x2) + $depX]
	set select(y1) [expr $select(y1) + $depY]
	set select(y2) [expr $select(y2) + $depY]

	for {set i 0} {$i<[llength $select(listePlace)]} {incr i} {
	    set laPlace [lindex $select(listePlace) $i]
	    set tabPlace($tpn(courant),$laPlace,xy,x) [posSurGrille [expr $tabPlace($tpn(courant),$laPlace,xy,x) + $depX]]
	    set tabPlace($tpn(courant),$laPlace,xy,y) [posSurGrille [expr $tabPlace($tpn(courant),$laPlace,xy,y) + $depY]] 
	}
	for {set i 0} {$i<[llength $select(listeNoeud)]} {incr i} {
	    if {[lindex $select(listeNoeud) $i]>0}	 {  modifRelativePositionNoeud $depX $depY [lindex $select(listeNoeud) $i]}
	}
	for {set i 0} {$i<[llength $select(listeTransition)]} {incr i} {
	    set laTransition [lindex $select(listeTransition) $i]
	    set tabTransition($tpn(courant),$laTransition,xy,x) [posSurGrille [expr $tabTransition($tpn(courant),$laTransition,xy,x) + $depX]]
	    set tabTransition($tpn(courant),$laTransition,xy,y) [posSurGrille [expr $tabTransition($tpn(courant),$laTransition,xy,y) + $depY]]
	}
	redessinerRdP $c
    }
  }
}

# COLLER :
proc copierLaSelection {w} {
    global tabPlace 
    global tabTransition
    global tpn tabUnDo
    global fin
    global ok
    global destroy
    global plot modif
    global select
    global maxX maxY
    global tempNoeud
    global simulatorOn

    
  if {$simulatorOn==0} {
    if {[llength $select(listeNoeud)]+[llength $select(listePlace)]+[llength $select(listeTransition)]>0} {
      if {$select(tpn) == $tpn(courant)} {


	if {[max $select(x1) $select(x2)] > $maxX-30} {set dx -26} else {set dx 26}
	if {[max $select(y1) $select(y2)] > $maxY-30} {set dy -26} else {set dy 26}

	modifTPN $tpn(courant)

	set modif(freeze) 1

	set tempNoeud(1,placeNPT) -1
	set tempNoeud(1,placeNTP) -1
	set tempNoeud(1,transitionNPT) -1
	set tempNoeud(1,transitionNTP) -1
	set tempNoeud(1,type) 0
    
	set select(x1) [expr $select(x1) + $dx]
	set select(x2) [expr $select(x2) + $dx]
	set select(y1) [expr $select(y1) + $dy]
	set select(y2) [expr $select(y2) + $dy]

	set copier(listePlace) $select(listePlace)
	set copier(listeLabelPlace) $select(listeLabelPlace)
	set copier(listeTransition) $select(listeTransition)
	set copier(listeLabelTransition) $select(listeLabelTransition)
	set copier(listeNoeud) $select(listeNoeud)


	set select(listePlace) [list]
	set select(listeLabelPlace) [list]
	set select(listeTransition) [list]
	set select(listeLabelTransition) [list]
	set select(listeNoeud) [list]

	for {set i 0} {$i<[llength $copier(listePlace)]} {incr i} {
	    set laPlace [lindex $copier(listePlace) $i]
	    set indice [dupliquerPlace $laPlace $dx $dy]
	    lappend select(listePlace) $indice
	}

	for {set i 0} {$i<[llength $copier(listeTransition)]} {incr i} {
	    set laTransition [lindex $copier(listeTransition) $i]
	    set indice [dupliquerTransition $laTransition $copier(listePlace) $select(listePlace) $copier(listeNoeud) $dx $dy]
	    lappend select(listeTransition) $indice
	}

	redessinerLeTPNCourant
	
	for {set npt 1} {$tempNoeud($npt,placeNPT)>-1} {incr npt} {
	    lappend select(listeNoeud) [indiceNoeudPT $tempNoeud($npt,placeNPT) $tempNoeud($npt,transitionNPT) $tempNoeud($npt,type)]
	}
	for {set ntp 1} {$tempNoeud($ntp,placeNTP)>-1} {incr ntp} {
	    lappend select(listeNoeud) [indiceNoeudTP $tempNoeud($ntp,transitionNTP) $tempNoeud($ntp,placeNTP)]
	}

	
	set modif(freeze) 0
#	redessinerProjet $c
     } elseif {$select(fenetre) == $w} {
	modifTPN $tpn(courant)

	set copier(listePlace) $select(listePlace)
	set copier(listeLabelPlace) $select(listeLabelPlace)
	set copier(listeTransition) $select(listeTransition)
	set copier(listeLabelTransition) $select(listeLabelTransition)
	set copier(listeNoeud) $select(listeNoeud)

	set select(listePlace) [list]
	set select(listeLabelPlace) [list]
	set select(listeTransition) [list]
	set select(listeLabelTransition) [list]
	set select(listeNoeud) [list]

	for {set i 0} {$i<[llength $copier(listePlace)]} {incr i} {
	    set laPlace [lindex $copier(listePlace) $i]

	    set indice [collerPlace $select(tpn) $laPlace $tpn(courant)]
	    lappend select(listePlace) $indice
	}

	for {set i 0} {$i<[llength $copier(listeTransition)]} {incr i} {
	    set laTransition [lindex $copier(listeTransition) $i]
	    set indice [collerTransition $select(tpn) $laTransition $copier(listePlace) $tpn(courant) $select(listePlace)]
	    lappend select(listeTransition) $indice
	}
	set select(tpn) $tpn(courant)
	set select(onglet) $tpn(onglet)
	set select(fenetre) $w

     }
	

	redessinerLeTPNCourant
   } 
  }
}

proc detruireLaSelection {c} {
    global tabPlace 
    global tabTransition
    global tpn tabUnDo
    global fin
    global ok
    global destroy
    global plot
    global select modif
    global maxX maxY
    global simulatorOn

  if {$simulatorOn==0} {
    modifTPN $tpn(courant)
    set modif(freeze) 1
    set select(vide) 1

    for {set i 0} {$i<[llength $select(listeNoeud)]} {incr i} {
	supprimerNoeud [lindex $select(listeNoeud) $i]
    }
    for {set i 0} {$i<[llength $select(listePlace)]} {incr i} {
	set laPlace [lindex $select(listePlace) $i]
	supprimerPlace $laPlace
    }
    for {set i 0} {$i<[llength $select(listeTransition)]} {incr i} {
	supprimerTransition [lindex $select(listeTransition) $i]
    }
    set select(listePlace) [list]
    set select(listeLabelPlace) [list]
    set select(listeTransition) [list]
    set select(listeLabelTransition) [list]
    set select(listeNoeud) [list]
    set modif(freeze) 0
    redessinerRdP $c
  }
}

#----------------------Couleur-------------------------
proc changerCouleurDeLaSelection {} {
    global tabPlace 
    global tabTransition
    global tpn tabUnDo
    global fin
    global ok
    global destroy
    global plot
    global select
    global maxX maxY
    global couleurCourante

  for {set i 0} {$i<[llength $select(listePlace)]} {incr i} {
	set laPlace [lindex $select(listePlace) $i]
	set tabPlace($tpn(courant),$laPlace,color) $couleurCourante(Place)
   } 
   for {set i 0} {$i<[llength $select(listeTransition)]} {incr i} {
     set laTransition [lindex $select(listeTransition) $i]
	 set tabTransition($tpn(courant),$laTransition,color) $couleurCourante(Transition)
    
     for {set j 1} {$tabTransition($tpn(courant),$laTransition,Porg,$j)!=0} {incr j} {
	    set iPo [lsearch $select(listePlace) $tabTransition($tpn(courant),$laTransition,Porg,$j)]
	    if {$iPo!=(-1)} {
	     set tabTransition($tpn(courant),$laTransition,PorgColor,$j) $couleurCourante(Arc)
	    } 
     }

     for {set j 1} {$tabTransition($tpn(courant),$laTransition,Pdes,$j)!=0} {incr j} {
	    set iPo [lsearch $select(listePlace) $tabTransition($tpn(courant),$laTransition,Pdes,$j)]
	    if {$iPo!=-1} {
	     set tabTransition($tpn(courant),$laTransition,PdesColor,$j) $couleurCourante(Arc)
	    } 
     }
   }
}

#***********************************************************


proc max {a b} {
    if {$a >$b} {
	return $a
    } else {
	return $b
    }
}
proc min {a b} {
    if {$a < $b} {
	return $a
    } else {
	return $b
    }
}

proc signe {x} {
    #  if {(($x -$y)>7) || ( ($y - $x)>7 )} {
    #    set resultat [expr ($x+$y)/2]
    #  } elseif {($x -$y)>0} {}
    if {($x)<0} {set resultat -1} else {set resultat 1}

    return $resultat
}

proc moyMax {x y} {
    #  if {(($x -$y)>7) || ( ($y - $x)>7 )} {
    #    set resultat [expr ($x+$y)/2]
    #  } elseif {($x -$y)>0} {}
    if {($x -$y)>0} {
	set resultat [expr ($x+$y)/2 + 5]
    } else {set resultat [expr ($x+$y)/2 - 5]}
    return $resultat
}

