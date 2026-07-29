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

# procedure du parsing xml
# lireAttribut, elementDebut, elementFin
# insererPlace, insererTransition, arcPlaceTransition, arcTransitionPlace
# razElementCourant, ouvrirPointXML
# ajusteTaille


#********************** lire la valeur d'un attribut *********************

proc lireAttribut {liste attribut defaut} {
    if {[lsearch $liste $attribut]!=-1} {
	return [lindex $liste [expr [lsearch $liste $attribut]+1]]
    } else {return $defaut}
}

#********************** ouverture de balise *****************************

proc elementDebut {nomBalise attributs args } {
    global idPC idTC identifierC
    global labelC initialMarkingC
    global xC yC
    global eftC lftC eftPC lftPC obsC unctrlC eftInclC lftInclC
    global minC maxC
    global costC deltaCostxC deltaCostyC
    global prioC speedC deltaSpeedxC deltaSpeedyC
    global deltaxC deltayC deltaGuardxC deltaGuardyC deltaUpdatexC deltaUpdateyC
    global gammaC omegaC
    global typeArcC xnailC ynailC
    global weightArc inhibitingCondition tokenColorArc
    global couleur
    global infini
    global moduloP moduloT conserverCouleur
    global tabColor
    global constraintC
    global synchronized
    global updateC guardC romeoVersionC
    global ladata ladataAvecBalise
    global nbinput nbopen nbinclude idInput fileInput statusInput idInclude fileInclude



    switch $nomBalise {
	romeo {
	    set romeoVersionC [lireAttribut $attributs version ""]
	}
	place {
	    set idPC [expr [lireAttribut $attributs id 0] + $moduloP]
	    set identifierC [lireAttribut $attributs identifier "P$idPC"]
	    set labelC [lireAttribut $attributs label "P$idPC"]
	    set eftPC [lireAttribut $attributs eft 0]
	    set lftPC [lireAttribut $attributs lft inf]
	    set initialMarkingC [lireAttribut $attributs initialMarking 0]
	}
	transition {
	    set idTC [expr [lireAttribut $attributs id 0] + $moduloT]
	    set identifierC [lireAttribut $attributs identifier "T$idTC"]
	    set labelC [lireAttribut $attributs label "T$idTC"]
	    set eftC [lireAttribut $attributs eft 0]	   
	    set lftC [lireAttribut $attributs lft 0]
	    set eftInclC [lireAttribut $attributs eftIncl 1]	   
	    set lftInclC [lireAttribut $attributs lftIncl 1]
	    set prioC [lireAttribut $attributs priority 0]
	    set speedC [lireAttribut $attributs speed 1]
	    set costC [lireAttribut $attributs cost 0]
	    set minC [lireAttribut $attributs eft_param ""]
	    set maxC [lireAttribut $attributs lft_param ""]
	    set obsC [lireAttribut $attributs obs 1]
	    set unctrlC [lireAttribut $attributs unctrl 0]
#set guardC ""
	    set guardC [remettrePartoutInfSupEq [lireAttribut $attributs guard ""]]
	    set updateC ""
#	    set updateC [lireAttribut $attributs update ""]
	}
	update {
	    set ladata ""
	    set ladataAvecBalise ""
	}    
	arc {
	    set idPC [expr [lireAttribut $attributs place 0] + $moduloP]
	    # set idPC [lireAttribut $attributs place error]
	    set idTC [expr [lireAttribut $attributs transition 0] + $moduloT]
	    #	set idTC [lireAttribut $attributs transition error]
	    set typeArcC [lireAttribut $attributs type error]
	    set weightArc [lireAttribut $attributs weight error]
	    set tokenColorArc [lireAttribut $attributs tokenColor 0]
	    if {$typeArcC!="transitionPlace"} {
		set inhibitingCondition [remettrePartoutInfSupEq [lireAttribut $attributs inhibitingCondition ""]]
	    }
	}
	position {
	    set xC [lireAttribut $attributs x 100]
	    set yC [lireAttribut $attributs y 100]
	    if {($xC!=100)||($yC!=100)} {set ::infoGraphique 1}
	}
	deltaGuard {
	    set deltaGuardxC [lireAttribut $attributs deltax 0]
	    set deltaGuardyC [lireAttribut $attributs deltay 0]
	}
	deltaUpdate {
	    set deltaUpdatexC [lireAttribut $attributs deltax 0]
	    set deltaUpdateyC [lireAttribut $attributs deltay 0]
	}
	deltaSpeed {
	    set deltaSpeedxC [lireAttribut $attributs deltax 10]
	    set deltaSpeedyC [lireAttribut $attributs deltay 0]
	}
	deltaCost {
	    set deltaCostxC [lireAttribut $attributs deltax 10]
	    set deltaCostyC [lireAttribut $attributs deltay 0]
	}
	deltaLabel {
	    set deltaxC [lireAttribut $attributs deltax 0]
	    set deltayC [lireAttribut $attributs deltay 0]
	}
	scheduling {
	    set gammaC [lireAttribut $attributs gamma 0]
	    set omegaC [lireAttribut $attributs omega 0]
	}
        constraint {
	    set constraintC [lireAttribut $attributs left ""]
	    set constraintC [format "%s%s" $constraintC [lireAttribut $attributs op ""]]
	    set constraintC [format "%s%s" $constraintC [lireAttribut $attributs right ""]]

            set constraintC [string map -nocase {
		"LowerOrEqual"      "<="
		"GreaterOrEqual"      ">="
		"Lower"       "<"
		"Greater"       ">"
		"Equal"	   "=="
	    } $constraintC]
	}
	misc {
	}
	nail {
	    set xnailC  [lireAttribut $attributs xnail 0]
	    set ynailC  [lireAttribut $attributs ynail 0]
	}
	TPN {
	}
	graphics {
	    set couleur  [lireAttribut $attributs color 0]
	}
	colorPlace {
	 if {$conserverCouleur==0} {
      for {set i 0} {$i <= 5} {incr i} {
	    set tabColor(Place,$i)  [lireAttribut $attributs c$i 0]
      }
     }  
    }  
	colorTransition {
	 if {$conserverCouleur==0} {
      for {set i 0} {$i <= 5} {incr i} {
	    set tabColor(Transition,$i)  [lireAttribut $attributs c$i 0]
      } 
     } 
	}
	colorArc {
	 if {$conserverCouleur==0} {
      for {set i 0} {$i <= 5} {incr i} {
	    set tabColor(Arc,$i)  [lireAttribut $attributs c$i 0]
      }
     }  
	}
	synchronization {
            set synchronized [lireAttribut $attributs listSynch 0]
	}
	preferences {
	}
	declaration {
	    set ladata ""
	    set ladataAvecBalise ""
	}
	initialization {
	    set ladata ""
	    set ladataAvecBalise ""
	}	
	nbTokenColor {
	    set ladata ""
	}
	timedCost {
	    set ladata ""
	}
	project {
	    set nbinput [lireAttribut $attributs nbinput 0]
	    set nbopen [lireAttribut $attributs openinput 0]
	    set nbinclude [lireAttribut $attributs nbinclude 0]
#$projet($tpn(onglet),nbInput) 
	}
	input {
	    set idInput [lireAttribut $attributs id 0]
	    set fileInput [lireAttribut $attributs file ""]
	    set statusInput [lireAttribut $attributs status "closed"]
	}
	include {
	    set idInclude [lireAttribut $attributs id 0]
	    set fileInclude [lireAttribut $attributs file ""]
	}
	default {
	    erreurFichier $nomBalise TPN
	}
    }
}

proc procData {data} {
global ladata ladataAvecBalise


set ladataAvecBalise $ladata
set ladata $data
#puts "free $data"
}

#********************** fermeture de balise *****************************

proc elementFin {nomBalise} {
    global tabPlace tabTransition tabConstraint projet
    global declaration initialization timedCost nbTokenColor
    global tpn tabUnDo
    global nbProcesseur
    global nbConstraints
    global fin ok infini
    global idPC idTC identifierC
    global labelC initialMarkingC
    global eftC lftC eftPC lftPC eftInclC lftInclC
    global minC maxC obsC unctrlC
    global xC yC
    global costC deltaCostxC deltaCostyC
    global prioC speedC deltaSpeedxC deltaSpeedyC
    global deltaxC deltayC deltaGuardxC deltaGuardyC deltaUpdatexC deltaUpdateyC
    global gammaC omegaC
    global typeArcC xnailC ynailC 
    global weightArc inhibitingCondition tokenColorArc
    global couleur
    global constraintC
    global synchronized
    global ladata ladataAvecBalise
    global updateC guardC romeoVersionC
    global moduloP moduloT
    global nbinput nbopen nbinclude idInput fileInput statusInput idInclude fileInclude
    global pareseASlave

 

    switch $nomBalise {
	romeo {
# romeoVersionC contient la version de Romeo avec laquelle la sauvegarde a ete realisee
	}
	place {
	    insererPlace $idPC
	    set tabPlace($tpn(courant),$idPC,dmin) $eftPC
	    if {[string compare $lftPC "infini"]&&[string compare $lftPC "inf"]} {
		set tabPlace($tpn(courant),$idPC,dmax) $lftPC
	    } else {
		set tabPlace($tpn(courant),$idPC,dmax) $infini
	    }
	    set tabPlace($tpn(courant),$idPC,statut) $ok
	    set tabPlace($tpn(courant),$idPC,color) $couleur
	    set tabPlace($tpn(courant),$idPC,label,nom) [alphanumerique $labelC]
	    if {$identifierC!= ""} {
		set tabPlace($tpn(courant),$idPC,id) [alphanumerique $identifierC]
	    } else {	
		if {[string length $labelC]<10} { 
		    set tabPlace($tpn(courant),$idPC,id) [alphanumerique [genererUniquePlaceId $idPC $labelC]]
		} else {
		    set tabPlace($tpn(courant),$idPC,id) [alphanumerique [genererUniquePlaceId $idPC "P$idPC"]]
		}
	    }
	    set tabPlace($tpn(courant),$idPC,label,dx) $deltaxC
	    set tabPlace($tpn(courant),$idPC,label,dy) $deltayC
	    set tabPlace($tpn(courant),$idPC,processeur) $gammaC
	    set tabPlace($tpn(courant),$idPC,priorite) $omegaC
	    set tabPlace($tpn(courant),$idPC,jeton) $initialMarkingC
	    set tabPlace($tpn(courant),$idPC,xy,x) $xC
	    set tabPlace($tpn(courant),$idPC,xy,y) $yC
	    if {$nbProcesseur($tpn(courant)) < $gammaC} {set nbProcesseur($tpn(courant)) $gammaC}
	    razElementCourant
	}
	transition {
	    insererTransition $idTC
	    set tabTransition($tpn(courant),$idTC,statut) $ok
	    set tabTransition($tpn(courant),$idTC,color) $couleur
	    set tabTransition($tpn(courant),$idTC,dmin) $eftC
	    set tabTransition($tpn(courant),$idTC,eftIncl) $eftInclC	    
	    set tabTransition($tpn(courant),$idTC,lftIncl) $lftInclC
#	    set tabTransition($tpn(courant),$idTC,update) $updateC
	    if {[string compare $lftC "infini"]&&[string compare $lftC "infinity"]&&[string compare $lftC "inf"]} {
		set tabTransition($tpn(courant),$idTC,dmax) $lftC
	    } else {
		set tabTransition($tpn(courant),$idTC,dmax) $infini
	    }
	    set tabTransition($tpn(courant),$idTC,minparam) $minC
	    set tabTransition($tpn(courant),$idTC,maxparam) $maxC
	    set tabTransition($tpn(courant),$idTC,label,nom) [alphanumerique $labelC]
	    if {$identifierC!= ""} {
		set tabTransition($tpn(courant),$idTC,id) [alphanumerique $identifierC]
	    } else {	
		if {[string length $labelC]<10} { 
		    set tabTransition($tpn(courant),$idTC,id) [alphanumerique [genererUniqueTransId $idTC $labelC]]
		} else {
		    set tabTransition($tpn(courant),$idTC,id) [alphanumerique [genererUniqueTransId $idTC "T$idTC"]]
		}
	    }
	    set tabTransition($tpn(courant),$idTC,label,dx) $deltaxC
	    set tabTransition($tpn(courant),$idTC,label,dy) $deltayC
	    set tabTransition($tpn(courant),$idTC,guard,dx) $deltaGuardxC
	    set tabTransition($tpn(courant),$idTC,guard,dy) $deltaGuardyC
	    set tabTransition($tpn(courant),$idTC,update,dx) $deltaUpdatexC
	    set tabTransition($tpn(courant),$idTC,update,dy) $deltaUpdateyC
	    set tabTransition($tpn(courant),$idTC,speed,dx) $deltaSpeedxC
	    set tabTransition($tpn(courant),$idTC,speed,dy) $deltaSpeedyC
	    set tabTransition($tpn(courant),$idTC,cost,dx) $deltaCostxC
	    set tabTransition($tpn(courant),$idTC,cost,dy) $deltaCostyC
	    set tabTransition($tpn(courant),$idTC,xy,x) $xC
	    set tabTransition($tpn(courant),$idTC,xy,y) $yC
	    set tabTransition($tpn(courant),$idTC,obs) $obsC
	    set tabTransition($tpn(courant),$idTC,unctrl) $unctrlC
    	    set tabTransition($tpn(courant),$idTC,guard) $guardC
    	    set tabTransition($tpn(courant),$idTC,update) $updateC
    	    set tabTransition($tpn(courant),$idTC,speed) $speedC
    	    set tabTransition($tpn(courant),$idTC,priority) $prioC
    	    set tabTransition($tpn(courant),$idTC,cost) $costC
	    razElementCourant
	}
	update {
#	    if {($romeoVersionC == "oldVersion")&&($ladataAvecBalise == "")} 
	    if {$ladataAvecBalise == ""} {
		set ladataAvecBalise $ladata
	    }
	    set updateC $ladataAvecBalise
	}    
	arc {
#	    insererTransition $idTC
#	    insererPlace $idPC
	    if {[string compare $typeArcC "TransitionPlace"]} {
		arcPlaceTransition $idPC $idTC $xnailC $ynailC $weightArc $typeArcC $inhibitingCondition $couleur $tokenColorArc
	    } else {
		arcTransitionPlace $idPC $idTC $xnailC $ynailC $weightArc $couleur $tokenColorArc
	    }
	    razElementCourant
	}
	position {
	}
	deltaLabel {
	}
#	deltaGuard {
#	}
#	deltaUpdate {
#	}
	scheduling {
	}
        constraint {
	    if {[string length $tabConstraint($tpn(courant),0)] == 0 } {
		set idCC 0
	    } else {
		set idCC $nbConstraints($tpn(courant))
	        incr nbConstraints($tpn(courant))
	    }
	    set tabConstraint($tpn(courant),$idCC) $constraintC
	    razElementCourant
	}
	declaration {
#	    if {($romeoVersionC == "oldVersion")&&($ladataAvecBalise == "")} 
	    if {$ladataAvecBalise == ""} {
		set ladataAvecBalise $ladata
	    }
	    if {$ladataAvecBalise != ""} {
		set declaration($tpn(courant)) [remettreSupSupInfInf $ladataAvecBalise]
	    } else {
		set declaration($tpn(courant))  "// insert here your type definitions using C-like syntax


// insert here your function definitions 
// using C-like syntax"
	    }
	}
	initialization {
#	    if {($romeoVersionC == "oldVersion")&&($ladataAvecBalise == "")} 
	    if {$ladataAvecBalise == ""} {
		set ladataAvecBalise $ladata
	    }
	    if {$ladataAvecBalise != ""} {
		set initialization($tpn(courant)) [remettreSupSupInfInf $ladataAvecBalise]
	    } else {
		set initialization($tpn(courant)) "// insert here the state variables declarations 
// and possibly some code to initialize them 
// using C-like syntax"
	    }
	    set declaration($tpn(courant)) "$declaration($tpn(courant))\n\n initially \{\n $initialization($tpn(courant)) \n \}"
	}
	nbTokenColor {
	    if {$ladata != ""} {
		set nbTokenColor($tpn(courant)) $ladata
	    } else {
		set nbTokenColor($tpn(courant)) 0
	    }
	}
	timedCost {
	    if {$ladata != ""} {
		set timedCost($tpn(courant)) $ladata
	    } else {
		set timedCost($tpn(courant)) ""
	    }
	}
	project {
#	    set nbinput [lireAttribut $attributs nbinput 0]
#	    set nbopen [lireAttribut $attributs openinput 0]
#	    set nbinclude [lireAttribut $attributs nbinclude 0]

	    if {$pareseASlave==0} {
		set projet($tpn(onglet),nbInclude) $nbinclude
		set projet($tpn(onglet),nbInput) $nbinput
		set projet($tpn(onglet),nbOpen) $nbopen
	    }
	}
	input {
#	    set idInput [lireAttribut $attributs id 0]
#	    set fileInput [lireAttribut $attributs file ""]
#	    set statusInput [lireAttribut $attributs status "closed"]

	    if {$pareseASlave==0} {
		set projet($tpn(onglet),input,$idInput,file) $fileInput
		set projet($tpn(onglet),input,$idInput,status) $statusInput
	    }

	}
	include {
#	    set idInclude [lireAttribut $attributs id 0]
#	    set fileInclude [lireAttribut $attributs file ""]
	    if {$pareseASlave==0} {
		set projet($tpn(onglet),include,$idInclude,file) $fileInclude
	    }
	}
	default {
	}
    }
}


#********************** inserer une place dans le tableau *******************

proc insererPlace {indicePlace} {
    global tabPlace
    global tpn tabUnDo
    global fin ok destroy
    global insertTPN
    global infini
    global nbPlaceMax

#    for {set j 1} {$tabPlace($tpn(courant),$j,statut)!=$fin} {incr j} {}
#puts "$nbPlaceMax et $indicePlace"
    if {$nbPlaceMax <= $indicePlace} {
	set tabPlace($tpn(courant),[expr $indicePlace+1],statut) $fin
	for {set i $nbPlaceMax} {$i <= $indicePlace} {incr i} {
	    set tabPlace($tpn(courant),$i,statut) $destroy
	    set tabPlace($tpn(courant),$i,color) 0
	    set tabPlace($tpn(courant),$i,label,nom) "not_defined"
	    set tabPlace($tpn(courant),$i,id) "not_defined_$i"
	    set tabPlace($tpn(courant),$i,label,dx) 0
	    set tabPlace($tpn(courant),$i,label,dy) 0
	    set tabPlace($tpn(courant),$i,processeur) 0
	    set tabPlace($tpn(courant),$i,priorite) 0
	    set tabPlace($tpn(courant),$i,jeton) 0
	    set tabPlace($tpn(courant),$i,xy,x) 100
	    set tabPlace($tpn(courant),$i,xy,y) 100
	    set tabPlace($tpn(courant),$i,dmin) 0
	    set tabPlace($tpn(courant),$i,dmax) $infini
	}
	set nbPlaceMax [expr $indicePlace+1]
    }
#    if {$tabPlace($tpn(courant),$indicePlace,statut)!=$ok} {
 #   	set tabPlace($tpn(courant),$indicePlace,statut) $ok
  #  	set tabPlace($tpn(courant),$indicePlace,color) 0
 #       set tabPlace($tpn(courant),$indicePlace,label,nom) "not_defined"
  #      set tabPlace($tpn(courant),$indicePlace,id) [genererUniquePlaceId $indicePlace "P$indicePlace"]
#   	set tabPlace($tpn(courant),$indicePlace,label,dx) 0
#   	set tabPlace($tpn(courant),$indicePlace,label,dy) 0
#   	set tabPlace($tpn(courant),$indicePlace,processeur) 0
#   	set tabPlace($tpn(courant),$indicePlace,priorite) 0
#   	set tabPlace($tpn(courant),$indicePlace,jeton) 0
#   	set tabPlace($tpn(courant),$indicePlace,xy,x) 100
#   	set tabPlace($tpn(courant),$indicePlace,xy,y) 100
#	set tabPlace($tpn(courant),$indicePlace,dmin) 0
#	set tabPlace($tpn(courant),$indicePlace,dmax) $infini

#    }
}

#********************** inserer une transition dans le tableau *******************

proc insererTransition {indiceTransition} {
    global tabTransition
    global tpn tabUnDo
    global fin ok destroy
    global insertTPN
    global infini
   global nbTransitionMax

#    for {set j 1} {$tabTransition($tpn(courant),$j,statut)!=$fin} {incr j} {}
#puts "Transition $nbTransitionMax et $indiceTransition"

    if {$nbTransitionMax <= $indiceTransition} {
	set tabTransition($tpn(courant),[expr $indiceTransition+1],statut) $fin
	for {set i $nbTransitionMax} {$i <= $indiceTransition} {incr i} {
	    set tabTransition($tpn(courant),$i,statut) $destroy
	    set tabTransition($tpn(courant),$i,color) 0
	    set tabTransition($tpn(courant),$i,dmin) 0
	    set tabTransition($tpn(courant),$i,dmax) $infini
	    set tabTransition($tpn(courant),$i,speed) 1
	    set tabTransition($tpn(courant),$i,priority) 0
	    set tabTransition($tpn(courant),$i,cost) 0
	    set tabTransition($tpn(courant),$i,minparam) ""
	    set tabTransition($tpn(courant),$i,maxparam) ""
	    set tabTransition($tpn(courant),$i,label,nom) "not_defined"
	    set tabTransition($tpn(courant),$i,id) "not_defined$i"
	    set tabTransition($tpn(courant),$i,Porg,1) 0
	    set tabTransition($tpn(courant),$i,PorgInhibitingCondition,1) ""
	    set tabTransition($tpn(courant),$i,PorgWeight,1) 0
	    set tabTransition($tpn(courant),$i,PorgNailx,1) 0
	    set tabTransition($tpn(courant),$i,PorgNaily,1) 0
	    set tabTransition($tpn(courant),$i,PorgColor,1) 0
	    set tabTransition($tpn(courant),$i,PorgType,1) 0
	    set tabTransition($tpn(courant),$i,Pdes,1) 0
	    set tabTransition($tpn(courant),$i,PdesWeight,1) 0
	    set tabTransition($tpn(courant),$i,PdesNailx,1) 0
	    set tabTransition($tpn(courant),$i,PdesNaily,1) 0
	    set tabTransition($tpn(courant),$i,PdesColor,1) 0
	    set tabTransition($tpn(courant),$i,label,dx) 10
	    set tabTransition($tpn(courant),$i,label,dy) 10
	    set tabTransition($tpn(courant),$i,guard,dx) 10
	    set tabTransition($tpn(courant),$i,guard,dy) 20
	    set tabTransition($tpn(courant),$i,update,dx) 10
	    set tabTransition($tpn(courant),$i,update,dy) 30
	    set tabTransition($tpn(courant),$i,speed,dx) -20
	    set tabTransition($tpn(courant),$i,speed,dy) 5
	    set tabTransition($tpn(courant),$i,cost,dx) -20
	    set tabTransition($tpn(courant),$i,cost,dy) 5
	    set tabTransition($tpn(courant),$i,xy,x) 100
	    set tabTransition($tpn(courant),$i,xy,y) 100
	    set tabTransition($tpn(courant),$i,obs) 1
	    set tabTransition($tpn(courant),$i,unctrl) 0
	    set tabTransition($tpn(courant),$i,guard) ""
	    set tabTransition($tpn(courant),$i,update) ""
	    set tabTransition($tpn(courant),$i,PdesTokenColor,1) -1
	    set tabTransition($tpn(courant),$i,PorgTokenColor,1) -1
	    set tabTransition($tpn(courant),$i,eftIncl) 1
	    set tabTransition($tpn(courant),$i,lftIncl) 1

	    
	}
	set nbTransitionMax [expr $indiceTransition+1]
    }
#    if {$tabTransition($tpn(courant),$indiceTransition,statut)!=$ok} {
#	set tabTransition($tpn(courant),$indiceTransition,Porg,1) 0
#	set tabTransition($tpn(courant),$indiceTransition,PorgInhibitingCondition,1) ""
#	set tabTransition($tpn(courant),$indiceTransition,PorgWeight,1) 0
#	set tabTransition($tpn(courant),$indiceTransition,PorgNailx,1) 0
#	set tabTransition($tpn(courant),$indiceTransition,PorgNaily,1) 0
#	set tabTransition($tpn(courant),$indiceTransition,PorgType,1) 0
#	set tabTransition($tpn(courant),$indiceTransition,PorgColor,1) 0
#	set tabTransition($tpn(courant),$indiceTransition,Pdes,1) 0
#	set tabTransition($tpn(courant),$indiceTransition,PdesWeight,1) 0
#	set tabTransition($tpn(courant),$indiceTransition,PdesNailx,1) 0
#	set tabTransition($tpn(courant),$indiceTransition,PdesNaily,1) 0
#	set tabTransition($tpn(courant),$indiceTransition,PdesColor,1) 0
 #   }
}

#********************** ajouter un arc *******************

proc arcTransitionPlace {IP IT xnail ynail weight color tokenColor} {
    global tabPlace
    global tpn tabUnDo
    global tabTransition
    global fin ok destroy

    set existeDeja 0

    for {set j 1} {$tabTransition($tpn(courant),$IT,Pdes,$j) >0}   {incr j} {
	if {$tabTransition($tpn(courant),$IT,Pdes,$j) == $IP} {set existeDeja 1}
    }
    if {$existeDeja==0} {
	set tabTransition($tpn(courant),$IT,Pdes,$j) $IP
	set tabTransition($tpn(courant),$IT,PdesWeight,$j) $weight
	set tabTransition($tpn(courant),$IT,PdesNailx,$j) $xnail
	set tabTransition($tpn(courant),$IT,PdesNaily,$j) $ynail
	set tabTransition($tpn(courant),$IT,PdesColor,$j) $color
	set tabTransition($tpn(courant),$IT,PdesTokenColor,$j) $tokenColor
	set tabTransition($tpn(courant),$IT,Pdes,[expr $j+1]) 0
	set tabTransition($tpn(courant),$IT,PdesNailx,[expr $j+1]) 0
	set tabTransition($tpn(courant),$IT,PdesNaily,[expr $j+1]) 0
	set tabTransition($tpn(courant),$IT,PdesWeight,[expr $j+1]) 1      
	set tabTransition($tpn(courant),$IT,PdesColor,[expr $j+1]) $color
	set tabTransition($tpn(courant),$IT,PdesTokenColor,[expr $j+1]) -1
    }
}

proc arcPlaceTransition {IP IT xnail ynail weight type inhibitingCondition color tokenColor} {
    global tabPlace
    global tpn tabUnDo
    global tabTransition
    global fin ok destroy

    set existeDeja 0

    for {set j 1} {$tabTransition($tpn(courant),$IT,Porg,$j) >0}   {incr j} {
	if {($tabTransition($tpn(courant),$IT,Porg,$j) == $IP)} {
	    if {($tabTransition($tpn(courant),$IT,PorgType,$j)==[retrouverType $type])} { set existeDeja 1 }
	}
    }
    if {$existeDeja==0} {
	set tabTransition($tpn(courant),$IT,Porg,$j) $IP
	set tabTransition($tpn(courant),$IT,PorgInhibitingCondition,$j) $inhibitingCondition
	set tabTransition($tpn(courant),$IT,PorgWeight,$j) $weight
	set tabTransition($tpn(courant),$IT,PorgNailx,$j) $xnail
	set tabTransition($tpn(courant),$IT,PorgNaily,$j) $ynail
	set tabTransition($tpn(courant),$IT,PorgColor,$j) $color
	set tabTransition($tpn(courant),$IT,PorgTokenColor,$j) $tokenColor
	set tabTransition($tpn(courant),$IT,Porg,[expr $j+1]) 0
	set tabTransition($tpn(courant),$IT,PorgType,$j) [retrouverType $type]
	set tabTransition($tpn(courant),$IT,PorgNailx,[expr $j+1]) 0
	set tabTransition($tpn(courant),$IT,PorgNaily,[expr $j+1]) 0
	set tabTransition($tpn(courant),$IT,PorgInhibitingCondition,[expr $j+1]) ""
	set tabTransition($tpn(courant),$IT,PorgWeight,[expr $j+1]) 1
	set tabTransition($tpn(courant),$IT,PorgType,[expr $j+1]) 0
	set tabTransition($tpn(courant),$IT,PorgColor,[expr $j+1]) $color
	set tabTransition($tpn(courant),$IT,PorgTokenColor,[expr $j+1]) -1
    }
}


proc retrouverType {type} {
 
 if {![string compare $type "PlaceTransition"]} {
	    set res 0
	} elseif {![string compare $type "flush"]} {
	    set res 1
	} elseif {![string compare $type "read"]} {
	    set res 2
	} elseif {![string compare $type "logicalInhibitor"]} {
	    set res 3
	} elseif {![string compare $type "timedInhibitor"]} {
	    set res 4
	} else { 
	    set res 0
	}
  return $res
}

#*************** raz des variables de parsing ***************************

proc razElementCourant {} {
    global idPC idTC identifierC
    global labelC initialMarkingC
    global eftC lftC eftPC lftPC eftInclC lftInclC
    global minC maxC
    global xC yC
    global costC deltaCostxC deltaCostyC
    global prioC speedC deltaSpeedxC deltaSpeedyC
    global deltaxC deltayC deltaGuardxC deltaGuardyC deltaUpdatexC deltaUpdateyC
    global gammaC omegaC
    global typeArcC xnailC ynailC
    global weightArc inhibitingCondition tokenColorArc
    global couleur
    global constraintC updateC guardC obsC unctrlC
    global ladata
    global nbinput nbopen nbinclude idInput fileInput statusInput idInclude fileInclude

    set idPC 0
    set identifierC ""
    set idTC 0
    set xC 100
    set yC 100
    set minC 0
    set maxC 0
    set labelC 0
    set initialMarkingC 0
    set deltaxC 10
    set deltayC 10
    set deltaGuardxC 20
    set deltaGuardyC -20
    set deltaUpdatexC 20
    set deltaUpdateyC 10
    set deltaSpeedxC -20
    set deltaSpeedyC 5
    set deltaCostxC -20
    set deltaCostyC 5
    set speedC 1
    set prioC 0
    set costC 0
    set gammaC 0
    set omegaC 0
    set typeArcC 0
    set xnailC 0
    set ynailC 0
    set weightArc 0
    set tokenColorArc 0
    set inhibitingCondition ""
    set couleur 0
    set constraintC 0
    set ladata ""
    set guardC ""
    set updateC ""
    set obsC 1
    set unctrlC 1
    set nbinput 0
    set nbopen 0
    set nbinclude 0
    set idInput 0
    set fileInput ""
    set statusInput "closed"
    set idInclude 0
    set fileInclude ""

}


#***************************** ouvrir file.xml ****************************
# si file =0 alors il ouvre la fenetre tkopenfile

proc ouvrirPointXML {w c insererTPN file} {
    global env
    global nomRdP projet viewOnglet
    global home
    global cheminFichiers
    global francais
    global tabPlace
    global tabTransition parameters
    global tpn tabUnDo viewOnglet
    global declaration initialization timedCost nbTokenColor
    global tabConstraint
    global nbConstraints
    global nbProcesseur
    global fin ok destroy
    global modif 
    global maxX
    global maxY
    # les parametres de la place en cours de définition
    global idPC idTC identifierC
    global labelC initialMarkingC
    global xC yC
    global costC deltaCostxC deltaCostyC
    global prioC speedC deltaSpeedxC deltaSpeedyC
    global deltaxC deltayC deltaGuardxC deltaGuardyC deltaUpdatexC deltaUpdateyC
    global gammaC omegaC romeoVersionC
    global typeArcC xnailC ynailC
    global weightArc inhibitingCondition tokenColorArc
    global couleur tabColor
    global parser
    global moduloP moduloT simulatorOn conserverCouleur
    global synchronized
#    global ladeclaration linitialization letimedCost
    global nbPlaceMax nbTransitionMax
    global nbinput nbopen nbinclude idInput fileInput statusInput idInclude fileInclude

    global pareseASlave

    set pareseASlave 0

    set romeoVersionC "oldVersion"

  if {$simulatorOn==1} {
    affiche "\n "
    affiche [mc "-Warning: Not allowed - Quit simulator first"]
  } else {
    set types {{"TPN file"     {.xml}      TEXT}}
    
  queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0

    
	if {![string compare $file "0"]} {
	   set file [tk_getOpenFile -initialdir $cheminFichiers -filetypes $types ]
	}
	if {[string compare $file ""]} {

	    #** souris en sablier
            $c configure -cursor watch
            update

	    # ******** recherche d'un parser XML **************

            if {[catch {package require expat 1.0}]} {
                if {[catch {package require xml}]} {
                    error [mc "Unable to load a XML parser"]
                    set button [tk_messageBox -icon error -message "Unable to load a XMLparser \n\nInstall    \"expat\" \n          or   \"ActiveTcl8.3.4.1\""]
                } else { set parser [::xml::parser] }
            } else {
		set parser [expat xmlparser]
            }
	    $parser configure -elementstartcommand elementDebut -characterdatacommand procData -elementendcommand elementFin 
#-endcdatasectioncommand glop -startcdatasectioncommand glop
	    

	    
	    # **********************************************

	    #     set fichier [slach "$file"]
	    set fichier $file


	    # set nbProcesseur($tpn(courant)) 0

	    # Statut des places : ok, detroy, ou fin

	    if {$insererTPN} {
	    set conserverCouleur 1
		for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {}
		set moduloP $i
		for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin} {incr i} {}
		set moduloT $i
		affiche "\n "
		affiche [format [mc "-merging PN with %s ..."] $fichier]
		modifTPN $tpn(courant)
		set nbPlaceMax  $moduloP
		set nbTransitionMax $moduloT

	    } else {
	        # ******* obtenir un onglet et l'affecter a tpn *****************
		# nouvelOnglet modifie la valeur de tpn et tabUnDo avec tabUnDo($tpn(courant)) = 0

	        nouvelOnglet $w $file

		set viewOnglet(zoom,$tpn(onglet)) 1
		set viewOnglet(X,$tpn(onglet)) 0
		set viewOnglet(Y,$tpn(onglet)) 0
		

		# on suppose qu'il n'y a pas d'input ni d'include dans ce projet
		set projet($tpn(onglet),nbInclude) 0
		set projet($tpn(onglet),include,0,file) ""
		set projet($tpn(onglet),nbInput) 0
		set projet($tpn(onglet),nbOpen) 0
		set projet($tpn(onglet),input,0,file) ""
		set projet($tpn(onglet),input,0,status) "closed"

             	# ******* reinitialisation du RDP *****************
	        set conserverCouleur 0
		set nomRdP($tpn(onglet)) $fichier
		set moduloP 0
		set moduloT 0
		set tabPlace($tpn(courant),1,statut) $fin
		set tabTransition($tpn(courant),1,statut) $fin
		set tabConstraint($tpn(courant),0) ""
		set nbConstraints($tpn(courant)) 1
		set nbProcesseur($tpn(courant)) 0
		set declaration($tpn(courant)) ""
		set initialization($tpn(courant)) ""
		set nbTokenColor($tpn(courant)) 0
		set timedCost($tpn(courant)) ""
		queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0
#		$w.ligneDuBas.indication.nomRdp config -text [format [mc "TPN: %s"] $nomRdP($tpn(onglet))]
		affiche "\n"
		affiche  [mc "-Opening "]
		afficheBleu " $fichier"
		affiche  " ..."
		set modif($tpn(courant)) 0
	    set nbPlaceMax 1
	    set nbTransitionMax 1
	    }

	    set ::infoGraphique 0
	    razElementCourant

	    set file [open $fichier r]
	    set xmldata [read $file]
	    $parser parse $xmldata
	    
#	    set declaration($tpn(courant)) [lireBaliseXML $xmldata "declaration"]

#	    set initialization($tpn(courant)) [lireBaliseXML $xmldata "initialization"]
	    close $file
            initParikh $tpn(courant)
	    heritageOuPas $tpn(courant)
	    if {[ajusteTaille]} {
		save_preferences
	    } 

	   
	    # ET Maintenant OPEN THE SLAVE
	    
	    set LeNbInput $projet($tpn(onglet),nbInput)

	    for {set i 1} {$i<=$LeNbInput}  {incr i} {
 		parserSlave $i
	    }
	    #*** souris normal  (plus en sablier)***
	    $c configure -cursor arrow

	    if {[absenceDonneesGraphiques]&&($LeNbInput==0)} {
		fautIlPlacer 0
	    } else {
		redessinerProjet .romeo.global
		affiche [mc "done"]
	    }
	}
	   

	    
  }
}


proc parserSlave {slave} {
   global env
    global nomRdP projet
    global home
    global cheminFichiers
    global francais
    global tabPlace
    global tabTransition parameters
    global tpn tabUnDo
    global declaration initialization timedCost nbTokenColor
    global tabConstraint
    global nbConstraints
    global nbProcesseur
    global fin ok destroy
    global modif 
    global maxX
    global maxY
    # les parametres de la place en cours de définition
    global idPC idTC identifierC
    global labelC initialMarkingC
    global xC yC
    global costC deltaCostxC deltaCostyC
    global prioC speedC deltaSpeedxC deltaSpeedyC
    global deltaxC deltayC deltaGuardxC deltaGuardyC deltaUpdatexC deltaUpdateyC
    global gammaC omegaC romeoVersionC
    global typeArcC xnailC ynailC
    global weightArc inhibitingCondition tokenColorArc
    global couleur tabColor
    global parser
    global moduloP moduloT simulatorOn conserverCouleur
    global nbPlaceMax nbTransitionMax
    global nbinput nbopen nbinclude idInput fileInput statusInput idInclude fileInclude
    global  pareseASlave 

   set pareseASlave 1

    set chemin [repertoire $nomRdP($tpn(onglet))]	

# on sauvegarde d'abord l'etat du projet
 #   set etatProj(nbInclude) $projet($tpn(onglet),nbInclude)
  #  set etatProj(nbInput) $projet($tpn(onglet),nbInput)
   # set etatProj(nbOpen) $projet($tpn(onglet),nbOpen) 


    set fichier "$chemin\/$projet($tpn(onglet),input,$slave,file)"
    set tpn(slave) $slave
#		set tabUnDo([expr $tpn(onglet)*10+$i],courant) 0
#		set tabUnDo([expr $tpn(onglet)*10+$i],taille) 0
    set tpn(courant) [calculTPNCourant $slave]
    set nomRdP($tpn(courant)) $fichier
    set tabPlace($tpn(courant),1,statut) $fin
    set tabTransition($tpn(courant),1,statut) $fin
    set tabConstraint($tpn(courant),0) ""
    set nbConstraints($tpn(courant)) 1
    set nbProcesseur($tpn(courant)) 0
    set declaration($tpn(courant)) ""
    set initialization($tpn(courant)) ""
    set timedCost($tpn(courant)) ""
    set nbTokenColor($tpn(courant)) 0
    
    set nbPlaceMax 1
    set nbTransitionMax 1
    razElementCourant

    set modif($tpn(courant)) 0

    set file [open $fichier r]
    set xmldata [read $file]
    $parser parse $xmldata
    close $file

# on remet l'etat du projet
 #   set projet($tpn(onglet),nbInclude) 0
  #  set projet($tpn(onglet),include,0,file) $etatProj(nbInclude)
   # set projet($tpn(onglet),nbInput) $etatProj(nbInput) 
    #set projet($tpn(onglet),nbOpen) $etatProj(nbOpen)


}

proc parserPointXML {leTPN file} {
    global env
    global nomRdP projet
    global modif
    global home
    global cheminFichiers
    global francais
    global tabPlace
    global tabTransition
    global tpn tabUnDo
    global tabConstraint
    global nbConstraints
    global nbProcesseur 
    global fin ok destroy
    global modif
    global maxX
    global maxY
    # les parametres de la place en cours de définition
    global idPC idTC identifierC
    global labelC initialMarkingC
    global xC yC
    global costC deltaCostxC deltaCostyC
    global prioC speedC deltaSpeedxC deltaSpeedyC
    global deltaxC deltayC deltaGuardxC deltaGuardyC deltaUpdatexC deltaUpdateyC
    global gammaC omegaC
    global typeArcC xnailC ynailC
    global weightArc inhibitingCondition tokenColorArc
    global couleur tabColor
    global parser
    global moduloP moduloT simulatorOn conserverCouleur
    global synchronized
    global tabUnDo

#    set saveTPN $tpn
#    set tpn $leTPN
    set saveTPN(onglet) $tpn(onglet)
    set saveTPN(courant) $tpn(courant)
    set tpn(onglet) $leTPN(onglet)
    set tpn(courant) $leTPN(courant)
#    set projet($tpn(onglet)) $leProjet(courant)

    set types {{"TPN file"     {.xml}      TEXT}}
       if {![string compare $file "0"]} {
	   set file [tk_getOpenFile -initialdir $cheminFichiers -filetypes $types ]
	}
	if {[string compare $file ""]} {

	    # ******** recherche d'un parser XML **************

            if {[catch {package require expat 1.0}]} {
                if {[catch {package require xml}]} {
                    error [mc "Unable to load a XML parser"]
                    set button [tk_messageBox -icon error -message "Unable to load a XMLparser \n\nInstall    \"expat\" \n          or   \"ActiveTcl8.3.4.1\""]
                } else { set parser [::xml::parser] }
            } else {
		set parser [expat xmlparser]
            }
	    $parser configure -elementstartcommand elementDebut -characterdatacommand procData -elementendcommand elementFin

	    
	    # **********************************************

	    #     set fichier [slach "$file"]
	    set fichier $file

		set nomRdP($tpn(onglet)) $fichier
		set moduloP 0
		set moduloT 0
		set tabPlace($tpn(courant),1,statut) $fin
		set tabTransition($tpn(courant),1,statut) $fin
		set tabConstraint($tpn(courant),0) ""
		set nbConstraints($tpn(courant)) 1
		set nbProcesseur($tpn(courant)) 0
	    razElementCourant
	    set file [open $fichier r]
	    set xmldata [read $file]
	    $parser parse $xmldata
	    close $file
	    set tpn(onglet) $saveTPN(onglet)
	    set tpn(courant) $saveTPN(courant)

 }


}


#        }
#}

proc erreurFichier {balise attendu} {
    .romeo.frame.c configure -cursor ""
    update
    affiche "\n *error : \"$balise\" founded"
    error "\"$balise\" founded ??? not a $attendu file"
    set button [tk_messageBox -icon error -message "this file isn't a $attendu file"]
}

proc ajusteTaille {} {
    global maxX maxY
    set changeTaille 0
    if {$maxX < [tailleX]+50} {
	set maxX [expr [tailleX]+50]
	set changeTaille 1
    }
    if {$maxY < [tailleY]+50} {
	set maxY [expr [tailleY]+50]
	set changeTaille 1
    }
    if {$maxX < 600} {
	set maxX 600
	set changeTaille 1
    }
    if {$maxY < 350} {
	set maxY 350
	set changeTaille 1
    }
    if {$maxX > 1000000} {
	set maxX 1000000
	set changeTaille 1
    }
    if {$maxY > 1000000} {
	set maxY 1000000
	set changeTaille 1
    }
    return $changeTaille
}


#*****************************************parse property *********************************************

proc elementDebutProperty {nomBalise attributs } {
    global theProperty
    global ligneProperty
    
    switch $nomBalise {
	Properties {
	}
	place {
	    set indicePlace [lireAttribut $attributs id 0]
	    set operator [lireAttribut $attributs op 0]
	    set valeur [lireAttribut $attributs value 0]
	    if {[string compare $ligneProperty ""]} {
		set ligneProperty "$ligneProperty and M($indicePlace) [convertOperator $operator] $valeur"  
	    } else {  set ligneProperty "M($indicePlace) [convertOperator $operator] $valeur"   }
	}
	MarkingCondition {
	    set ligneProperty ""
	}
	default { 
	    erreurFichier $nomBalise Property
	}
    }
}

proc procDataProperty {data} {
}

#********************** fermeture de balise *****************************

proc elementFinProperty {nomBalise} {
    global theProperty
    global ligneProperty
    
    switch $nomBalise {
	Properties {
	}
	place {
	}
	MarkingCondition {
	    if {[string compare $theProperty ""]} {
		set theProperty "$theProperty or $ligneProperty"  
	    } else {  set theProperty $ligneProperty }
	}
	default { 
	    erreurFichier $nomBalise
	}
	default {
	}
    }
}


proc ouvrirPropertyXml {} {
    global env
    global nomRdP
    global home
    global cheminFichiers
    global parser
    global theProperty
    global fileProperty
    
    set theProperty ""  
    set types {
	{"Property file"     {.xml}      TEXT}
    }
    set file [tk_getOpenFile -initialdir $cheminFichiers -filetypes $types ]
    if {[string compare $file ""]} {

	# ******** recherche d'un parser XML **************

	if {[catch {package require expat 1.0}]} {
	    if {[catch {package require xml}]} {
		error "unable to load a XMLparser"
		set button [tk_messageBox -icon error -message "Unable to load a XMLparser \n\n\
Install    \"expat\" \n          or   \"ActiveTcl8.3.4.1\""]
	    } else { set parser [::xml::parser] }
	} else {
	    set parser [expat xmlparser]
	}
	$parser configure -elementstartcommand elementDebutProperty \
	    -characterdatacommand procDataProperty -elementendcommand elementFinProperty

	
	# **********************************************
	set fichier $file

	set file [open $fichier r]
	set xmldataProperty [read $file]
	$parser parse $xmldataProperty
	close $file 
	set fileProperty $fichier
    }
    return $theProperty
}


proc convertOperator {operator} {

    switch $operator {
	Greater  { set op ">" }
	Lower  { set op "<"  }
	GreaterOrEqual { set op ">=" }
	LowerOrEqual { set op "<="   }
	Equal  { set op "="   }
	default {
	    set op ERREUR
	    #     puts $comp
	}
    }
    return $op
}


# inutile maintenant ----------- A supprimer
#proc lireBaliseXML {chaine balise} {

#    set glop [supNextExpression $chaine "<$balise>"]
#    set glap [nextExpression $glop "<\/$balise>"]

#return $glap
#}

proc remplacerPartoutInfSupEq {phrase} { 

set leq [string map {<= #leq} $phrase]
set geq [string map {>= #geq} $leq]
set gneq [string map {> #greater} $geq]
set lneq [string map {< #lower} $gneq]
set eqeq [string map {== #eqeq} $lneq]

return [string map {!= #noteq} $eqeq]
}

proc remettrePartoutInfSupEq {phrase} { 

set leq [string map {#leq <=} $phrase]
set geq [string map {#geq >=} $leq]
set gneq [string map {#greater >} $geq]
set lneq [string map {#lower <} $gneq]
set eqeq [string map {#eqeq ==} $lneq]

return [string map {#noteq !=} $eqeq]

}

proc remettreSupSupInfInf {phrase} {
    return [string map {#supsupsingapour >>} [string map {#infinfsingapour <<} [string map {#infeqsingapour <=} [string map {#supeqsingapour >=} $phrase]]]]
}

proc retirerSupSupInfInf {phrase} {
    return [string map {>> #supsupsingapour} [string map {<< #infinfsingapour} [string map {<= #infeqsingapour} [string map {>= #supeqsingapour} $phrase]]]]
}

