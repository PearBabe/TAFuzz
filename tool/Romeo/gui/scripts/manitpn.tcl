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

# les procedures de modification du TPN et donc des tableaux tabPlace, tabTransition ...
#  creationPlace crationTransition....

#++operation sur les NOEUDS :
#  modifPositionNoeud , ajouterNoeudPT ajouterNoeudTP

#++ operation sur les ARCS :
#  supprimerArcPlaceTransition supprimerArcTransitionPlace

#++ DOUBLE CLICK sur place ou sur transition  : Definition des places, transitions ....
#++ REORDONNER TABLEAU PLACE ET TRANSITION :toutCommeYFaut

# dupliquerPlace dupliquerTransition...


#********************operation sur les NOEUDS***************


proc modifPositionWeightInhibCond {dxa dya xa ya numT} {
    global tabTransition 
    global tpn tabUnDo
    global tabFlechePT tabFlecheTP tabNoeud
    global fin

 	  set T $tabFlechePT($numT,transition)
	  set P $tabFlechePT($numT,place)
	  set type $tabFlechePT($numT,type)
 	  for {set i 1} { ($tabTransition($tpn(courant),$T,Porg,$i) != $P)||($tabTransition($tpn(courant),$T,PorgType,$i)!=$type)}  {incr i} {}

    if {$tabTransition($tpn(courant),$T,PorgNailx,$i)>0} {
	set tabTransition($tpn(courant),$T,PorgNailx,$i) [expr $tabTransition($tpn(courant),$T,PorgNailx,$i) + $dxa]
    } else {
	set tabTransition($tpn(courant),$T,PorgNailx,$i) $xa
    }
    if {$tabTransition($tpn(courant),$T,PorgNaily,$i)>0 } {
	set tabTransition($tpn(courant),$T,PorgNaily,$i) [expr $tabTransition($tpn(courant),$T,PorgNaily,$i) + $dya]
    } else {
	set tabTransition($tpn(courant),$T,PorgNaily,$i) $ya
    }


}


proc modifPositionNoeud {xa ya numNoeud} {
    global tabTransition 
    global tpn tabUnDo
    global tabFlechePT tabFlecheTP tabNoeud
    global fin
    
    if {$tabNoeud($numNoeud,TP)==-1} {
	  set T $tabFlechePT($tabNoeud($numNoeud,arc),transition)
	  set P $tabFlechePT($tabNoeud($numNoeud,arc),place)
	  set type $tabFlechePT($tabNoeud($numNoeud,arc),type)
 	  for {set i 1} { ($tabTransition($tpn(courant),$T,Porg,$i) != $P)||($tabTransition($tpn(courant),$T,PorgType,$i)!=$type)}  {incr i} {}
	  set tabTransition($tpn(courant),$T,PorgNailx,$i) $xa
	  set tabTransition($tpn(courant),$T,PorgNaily,$i) $ya
    } else {
	  set T $tabFlecheTP($tabNoeud($numNoeud,arc),transition)
	  set P $tabFlecheTP($tabNoeud($numNoeud,arc),place)
	  for {set i 1} { $tabTransition($tpn(courant),$T,Pdes,$i) != $P}  {incr i} {}
	  set tabTransition($tpn(courant),$T,PdesNailx,$i) $xa
	  set tabTransition($tpn(courant),$T,PdesNaily,$i) $ya
    }
}


proc modifRelativePositionNoeud {relX relY numNoeud} {
    global tabTransition 
    global tpn tabUnDo
    global tabFlechePT tabFlecheTP tabNoeud
    global fin
    
    if {$tabNoeud($numNoeud,TP)==-1} {
	  set T $tabFlechePT($tabNoeud($numNoeud,arc),transition)
	  set P $tabFlechePT($tabNoeud($numNoeud,arc),place)
	  set type $tabFlechePT($tabNoeud($numNoeud,arc),type)
	  for {set i 1} {($tabTransition($tpn(courant),$T,Porg,$i) != $P)||($tabTransition($tpn(courant),$T,PorgType,$i) != $type)}  {incr i} {}
	  set tabTransition($tpn(courant),$T,PorgNailx,$i) [expr $tabTransition($tpn(courant),$T,PorgNailx,$i) + $relX]
	  set tabTransition($tpn(courant),$T,PorgNaily,$i) [expr $tabTransition($tpn(courant),$T,PorgNaily,$i) + $relY]
    } else {
	  set T $tabFlecheTP($tabNoeud($numNoeud,arc),transition)
	  set P $tabFlecheTP($tabNoeud($numNoeud,arc),place)
	  for {set i 1} { $tabTransition($tpn(courant),$T,Pdes,$i) != $P}  {incr i} {}
	  set tabTransition($tpn(courant),$T,PdesNailx,$i) [expr $tabTransition($tpn(courant),$T,PdesNailx,$i) + $relX]
	  set tabTransition($tpn(courant),$T,PdesNaily,$i) [expr $tabTransition($tpn(courant),$T,PdesNaily,$i) + $relY]
    }
}


proc supprimerNoeud {numNoeud} {
    global tabTransition 
    global tpn tabUnDo
    global tabFlechePT tabFlecheTP tabNoeud
    global destroy
    global fin
    global ok
    
    if {$tabNoeud($numNoeud,TP)==-1} {
	set T $tabFlechePT($tabNoeud($numNoeud,arc),transition)
	set P $tabFlechePT($tabNoeud($numNoeud,arc),place)
    set type $tabFlechePT($tabNoeud($numNoeud,arc),type)
	for {set j 1} {($tabTransition($tpn(courant),$T,Porg,$j) != $P)||($tabTransition($tpn(courant),$T,PorgType,$j) != $type)}  {incr j} {}
	set tabTransition($tpn(courant),$T,PorgNailx,$j) 0
	set tabTransition($tpn(courant),$T,PorgNaily,$j) 0
    } else {
	set T $tabFlecheTP($tabNoeud($numNoeud,arc),transition)
	set P $tabFlecheTP($tabNoeud($numNoeud,arc),place)
	for {set j 1} {$tabTransition($tpn(courant),$T,Pdes,$j) != $P}  {incr j} {}
	set tabTransition($tpn(courant),$T,PdesNailx,$j) 0
	set tabTransition($tpn(courant),$T,PdesNaily,$j) 0
    }
}

# ajouter un noeud dans un arc ++++++++++++

proc ajouterNoeudPT {P T type xa ya} {
    global tabTransition 
    global tpn tabUnDo
    global destroy
    global fin
    global ok modif
    
    modifTPN $tpn(courant)
    for {set j 1} { $tabTransition($tpn(courant),$T,Porg,$j) >0}  {incr j} {
        if {($tabTransition($tpn(courant),$T,Porg,$j)==$P)&&($tabTransition($tpn(courant),$T,PorgType,$j)==$type)} {
	    set tabTransition($tpn(courant),$T,PorgNailx,$j) $xa
	    set tabTransition($tpn(courant),$T,PorgNaily,$j) $ya
        }
    }
}


proc ajouterNoeudTP {T P xa ya} {
    global tabTransition 
    global tpn tabUnDo
    global destroy
    global fin
    global ok modif


    modifTPN $tpn(courant)
    for {set j 1} { $tabTransition($tpn(courant),$T,Pdes,$j) >0}  {incr j} {
        if {$tabTransition($tpn(courant),$T,Pdes,$j)==$P} {
	    set tabTransition($tpn(courant),$T,PdesNailx,$j) $xa
	    set tabTransition($tpn(courant),$T,PdesNaily,$j) $ya
        }
    }
}


#********************operation sur les ARCS ***************

proc supprimerArcPlaceTransition {P T type} {
    global tabTransition 
    global tpn tabUnDo
    global destroy
    global fin
    global ok modif

    modifTPN $tpn(courant)
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
	set onDecale 0
	for {set j 1} { $tabTransition($tpn(courant),$T,Porg,$j) >0}  {incr j} {
	    if {($tabTransition($tpn(courant),$T,Porg,$j)==$P)&&($tabTransition($tpn(courant),$T,PorgType,$j)==$type)} {set onDecale 1}
	    if {$onDecale==1} {
		set tabTransition($tpn(courant),$T,Porg,$j) $tabTransition($tpn(courant),$T,Porg,[expr $j+1])
		set tabTransition($tpn(courant),$T,PorgNailx,$j) $tabTransition($tpn(courant),$T,PorgNailx,[expr $j+1])
		set tabTransition($tpn(courant),$T,PorgNaily,$j) $tabTransition($tpn(courant),$T,PorgNaily,[expr $j+1])
		set tabTransition($tpn(courant),$T,PorgWeight,$j) $tabTransition($tpn(courant),$T,PorgWeight,[expr $j+1])
		set tabTransition($tpn(courant),$T,PorgInhibitingCondition,$j) $tabTransition($tpn(courant),$T,PorgInhibitingCondition,[expr $j+1])
		set tabTransition($tpn(courant),$T,PorgType,$j) $tabTransition($tpn(courant),$T,PorgType,[expr $j+1])
		set tabTransition($tpn(courant),$T,PorgColor,$j) $tabTransition($tpn(courant),$T,PorgColor,[expr $j+1])
		set tabTransition($tpn(courant),$T,PorgInhibitingCondition,$j) $tabTransition($tpn(courant),$T,PorgInhibitingCondition,[expr $j+1])
		set tabTransition($tpn(courant),$T,PorgTokenColor,$j) $tabTransition($tpn(courant),$T,PorgTokenColor,[expr $j+1])
	    }
	}
    }
}

proc supprimerArcTransitionPlace {T P} {
    global tabTransition 
    global tpn tabUnDo
    global destroy
    global fin
    global ok modif
    
    modifTPN $tpn(courant)
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
	set onDecale 0
	for {set j 1} { $tabTransition($tpn(courant),$T,Pdes,$j) >0}  {incr j} {
	    if {$tabTransition($tpn(courant),$T,Pdes,$j)==$P} {set onDecale 1}
	    if {$onDecale==1} {
		set tabTransition($tpn(courant),$T,Pdes,$j) $tabTransition($tpn(courant),$T,Pdes,[expr $j+1])
		set tabTransition($tpn(courant),$T,PdesNailx,$j) $tabTransition($tpn(courant),$T,PdesNailx,[expr $j+1])
		set tabTransition($tpn(courant),$T,PdesNaily,$j) $tabTransition($tpn(courant),$T,PdesNaily,[expr $j+1])
		set tabTransition($tpn(courant),$T,PdesWeight,$j) $tabTransition($tpn(courant),$T,PdesWeight,[expr $j+1])
		set tabTransition($tpn(courant),$T,PdesTokenColor,$j) $tabTransition($tpn(courant),$T,PdesTokenColor,[expr $j+1])
		set tabTransition($tpn(courant),$T,PdesColor,$j) $tabTransition($tpn(courant),$T,PdesColor,[expr $j+1])
	    }
	}
    }
}

proc ajouterArcPlaceTransition {laPlace laTransition type} {
   global tabTransition typePN tabPlace
   global tpn tabUnDo
   global destroy
   global fin
   global ok modif
   global couleurCourante
   global semExclusionElement

  if {($semExclusionElement==1)} {
     set semExclusionElement 0

   set existeDeja 0
   set onAnnule 0 
#   if {($tabPlace($tpn(courant),$laPlace,processeur)>0)&&[schedulingTransition $tpn(courant) $laTransition]} {
#       if {$typePN==-2} {
#	   set onAnnule 1
#	  set button [tk_messageBox -message "Transition $laTransition with 2 input scheduling Places"]
#
 #      } else {
#	   set tabPlace($tpn(courant),$laPlace,processeur) 0
#	   set tabPlace($tpn(courant),$laPlace,priorite) 0
 #      }
  # }
   if {$onAnnule==0} {
    modifTPN $tpn(courant)
    for {set j 1} {$tabTransition($tpn(courant),$laTransition,Porg,$j) >0}   {incr j} {
	if {($tabTransition($tpn(courant),$laTransition,Porg,$j) == $laPlace)&&($tabTransition($tpn(courant),$laTransition,PorgType,$j)==$type)} {
	    set existeDeja 1 
	    if {$tabTransition($tpn(courant),$laTransition,PorgType,$j)==0} {      
		if {$tabTransition($tpn(courant),$laTransition,PorgWeight,$j) == 0} {        
		    set tabTransition($tpn(courant),$laTransition,PorgWeight,$j) [expr $tabTransition($tpn(courant),$laTransition,PorgWeight,$j)+1]
		}
	    }
	}
    }
    if {$existeDeja==0} {
	set tabTransition($tpn(courant),$laTransition,Porg,$j) $laPlace
	set tabTransition($tpn(courant),$laTransition,PorgNailx,$j) 0
	set tabTransition($tpn(courant),$laTransition,PorgNaily,$j) 0
	set tabTransition($tpn(courant),$laTransition,PorgWeight,$j) 1
	set tabTransition($tpn(courant),$laTransition,PorgType,$j) $type
	set tabTransition($tpn(courant),$laTransition,PorgColor,$j) $couleurCourante(Arc)

	set tabTransition($tpn(courant),$laTransition,PorgTokenColor,$j) -1

	set tabTransition($tpn(courant),$laTransition,Porg,[expr $j+1]) 0
	set tabTransition($tpn(courant),$laTransition,PorgNailx,[expr $j+1]) 0
	set tabTransition($tpn(courant),$laTransition,PorgNaily,[expr $j+1]) 0
	set tabTransition($tpn(courant),$laTransition,PorgWeight,[expr $j+1]) 1
	set tabTransition($tpn(courant),$laTransition,PorgType,[expr $j+1]) 0
	set tabTransition($tpn(courant),$laTransition,PorgColor,[expr $j+1]) $couleurCourante(Arc)
	set tabTransition($tpn(courant),$laTransition,PorgTokenColor,[expr $j+1]) -1

	set tabTransition($tpn(courant),$laTransition,PorgInhibitingCondition,[expr $j+1]) ""  
    }
  }
      set semExclusionElement 1
  }
}

proc ajouterArcTransitionPlace {laTransition laPlace} {
    global tabTransition 
    global tpn tabUnDo
    global destroy
    global fin
    global ok modif
    global couleurCourante
    global semExclusionElement

  if {($semExclusionElement==1)} {
     set semExclusionElement 0
    
    modifTPN $tpn(courant)
    set existeDeja 0
    for {set j 1} {$tabTransition($tpn(courant),$laTransition,Pdes,$j) >0}   {incr j} {
	if {$tabTransition($tpn(courant),$laTransition,Pdes,$j) == $laPlace} {
	    set existeDeja 1
	    set tabTransition($tpn(courant),$laTransition,PdesWeight,$j) [expr $tabTransition($tpn(courant),$laTransition,PdesWeight,$j)+1]
	}
    }
    if {$existeDeja==0} {
	set tabTransition($tpn(courant),$laTransition,Pdes,$j)  $laPlace
	set tabTransition($tpn(courant),$laTransition,PdesNailx,$j) 0
	set tabTransition($tpn(courant),$laTransition,PdesNaily,$j) 0
	set tabTransition($tpn(courant),$laTransition,PdesWeight,$j) 1
	set tabTransition($tpn(courant),$laTransition,PdesColor,$j) $couleurCourante(Arc)

	set tabTransition($tpn(courant),$laTransition,PdesTokenColor,$j) -1

	set tabTransition($tpn(courant),$laTransition,Pdes,[expr $j+1]) 0
	set tabTransition($tpn(courant),$laTransition,PdesNailx,[expr $j+1]) 0
	set tabTransition($tpn(courant),$laTransition,PdesNaily,[expr $j+1]) 0
	set tabTransition($tpn(courant),$laTransition,PdesWeight,[expr $j+1]) 1
	set tabTransition($tpn(courant),$laTransition,PdesColor,[expr $j+1]) $couleurCourante(Arc)
	set tabTransition($tpn(courant),$laTransition,PdesTokenColor,[expr $j+1]) -1

    }
      set semExclusionElement 1
  }
}

#********************operation sur les PLACES ***************

# ************************ CREER PLACE **************************

proc creationPlace  {c absi ordo} {
    global tabPlace 
    global tpn tabUnDo nbTokenColor
    global fin ok
    global infini
    global modif
    global couleurCourante
    global semExclusionElement
    global eclair creerPlace


  if {($semExclusionElement==1)&&[winfo exists $c]} {
     set semExclusionElement 0
    modifTPN $tpn(courant)
    for {set i 1} {$tabPlace($tpn(courant),$i,statut)==$ok} {incr i} {}
    if {$tabPlace($tpn(courant),$i,statut)==$fin} {set tabPlace($tpn(courant),[expr $i+1],statut) $fin}

    set tabPlace($tpn(courant),$i,statut) $ok
    set tabPlace($tpn(courant),$i,color) $couleurCourante(Place)
    set tabPlace($tpn(courant),$i,xy,x) [posSurGrille $absi]
    set tabPlace($tpn(courant),$i,xy,y) [posSurGrille $ordo]
    set tabPlace($tpn(courant),$i,label,nom) "P$i"
    set tabPlace($tpn(courant),$i,id) [genererUniquePlaceId $i "P$i"]
    set tabPlace($tpn(courant),$i,label,dx) 10
    set tabPlace($tpn(courant),$i,label,dy) 10
    set tabPlace($tpn(courant),$i,processeur) 0
    set tabPlace($tpn(courant),$i,priorite) 0
    set tabPlace($tpn(courant),$i,dmin) 0
    set tabPlace($tpn(courant),$i,dmax) $infini

    set tabPlace($tpn(courant),$i,jeton) [ajusterTailleMarking 0 $nbTokenColor($tpn(courant))]

      if {$creerPlace==-2} {
	  set eclair(place) $i
      }
      
      redessinerRdP $c
 set semExclusionElement 1
}
}

# ********************* SUPPRIMER PLACE ***********************

proc supprimerPlace {numPlace} {
    global tabTransition 
    global tpn tabUnDo
    global tabPlace
    global destroy
    global fin
    global ok modif
   global semExclusionElement

  if {($semExclusionElement==1)} {
     set semExclusionElement 0

    modifTPN $tpn(courant)    
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
	
	if {$tabTransition($tpn(courant),$i,statut) == $ok} {
	    for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} {
		if {$tabTransition($tpn(courant),$i,Porg,$j)==$numPlace} {
		    set onDecale 0
		    while {$tabTransition($tpn(courant),$i,Porg,[expr $j+$onDecale])==$numPlace} {set onDecale [expr $onDecale+1]}
		    for {set k $j} {$tabTransition($tpn(courant),$i,Porg,[expr $k+$onDecale-1])>0}   {incr k} {
			 set tabTransition($tpn(courant),$i,Porg,$k) $tabTransition($tpn(courant),$i,Porg,[expr $k+$onDecale])
			 if {$tabTransition($tpn(courant),$i,Porg,[expr $k+$onDecale])!=0} {
			     set tabTransition($tpn(courant),$i,PorgNailx,$k) $tabTransition($tpn(courant),$i,PorgNailx,[expr $k+$onDecale])
			     set tabTransition($tpn(courant),$i,PorgNaily,$k) $tabTransition($tpn(courant),$i,PorgNaily,[expr $k+$onDecale])
			     set tabTransition($tpn(courant),$i,PorgWeight,$k) $tabTransition($tpn(courant),$i,PorgWeight,[expr $k+$onDecale])
			     set tabTransition($tpn(courant),$i,PorgInhibitingCondition,$k) $tabTransition($tpn(courant),$i,PorgInhibitingCondition,[expr $k+$onDecale])
			     set tabTransition($tpn(courant),$i,PorgType,$k) $tabTransition($tpn(courant),$i,PorgType,[expr $k+$onDecale])
			     set tabTransition($tpn(courant),$i,PorgColor,$k) $tabTransition($tpn(courant),$i,PorgColor,[expr $k+$onDecale])
			     set tabTransition($tpn(courant),$i,PorgTokenColor,$k) $tabTransition($tpn(courant),$i,PorgColor,[expr $k+$onDecale])
			 }
		     }

		}
	    }

	    set onDecale 0
	    for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} {
		if {$tabTransition($tpn(courant),$i,Pdes,$j)==$numPlace} {set onDecale 1}
		if {$onDecale==1} {
		    set tabTransition($tpn(courant),$i,Pdes,$j) $tabTransition($tpn(courant),$i,Pdes,[expr $j+1])
		    if {$tabTransition($tpn(courant),$i,Pdes,[expr $j+1])!=0} {
			set tabTransition($tpn(courant),$i,PdesNailx,$j) $tabTransition($tpn(courant),$i,PdesNailx,[expr $j+1])
			set tabTransition($tpn(courant),$i,PdesNaily,$j) $tabTransition($tpn(courant),$i,PdesNaily,[expr $j+1])
			set tabTransition($tpn(courant),$i,PdesWeight,$j) $tabTransition($tpn(courant),$i,PdesWeight,[expr $j+1])
			set tabTransition($tpn(courant),$i,PdesColor,$j) $tabTransition($tpn(courant),$i,PdesColor,[expr $j+1])
			set tabTransition($tpn(courant),$i,PdesTokenColor,$j) $tabTransition($tpn(courant),$i,PdesTokenColor,[expr $j+1])
		    }
		}
	    }
	}
    }
    set tabPlace($tpn(courant),$numPlace,statut) $destroy
set semExclusionElement 1
}
}

# ********************* CREER TRANSITION ***********************
proc creationTransition  {c absi ordo} {
    global tabTransition 
    global tpn tabUnDo
    global fin
    global ok infini
    global modif
    global couleurCourante
    global parikhVector
    global semExclusionElement
    global creerTransition eclair

  if {($semExclusionElement==1)&&[winfo exists $c]} {
     set semExclusionElement 0
    
    modifTPN $tpn(courant)
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)==$ok} {incr i} {}
    
    if {$tabTransition($tpn(courant),$i,statut)==$fin} {set tabTransition($tpn(courant),[expr $i+1],statut) $fin}
    set tabTransition($tpn(courant),$i,statut) $ok
    set tabTransition($tpn(courant),$i,color) $couleurCourante(Transition)
    set tabTransition($tpn(courant),$i,xy,x) [posSurGrille $absi]
    set tabTransition($tpn(courant),$i,xy,y) [posSurGrille $ordo]
    set tabTransition($tpn(courant),$i,Porg,1) 0
    set tabTransition($tpn(courant),$i,PorgNailx,1) 0
    set tabTransition($tpn(courant),$i,PorgNaily,1) 0
    set tabTransition($tpn(courant),$i,PorgWeight,1) 1
    set tabTransition($tpn(courant),$i,PorgInhibitingCondition,1) ""
    set tabTransition($tpn(courant),$i,PorgType,1) 0
    set tabTransition($tpn(courant),$i,PorgColor,1) $couleurCourante(Arc)
    set tabTransition($tpn(courant),$i,PorgTokenColor,1) -1
    set tabTransition($tpn(courant),$i,PdesTokenColor,1) -1
    set tabTransition($tpn(courant),$i,Pdes,1) 0
    set tabTransition($tpn(courant),$i,PdesNailx,1) 0
    set tabTransition($tpn(courant),$i,PdesNaily,1) 0
    set tabTransition($tpn(courant),$i,PdesWeight,1) 1
    set tabTransition($tpn(courant),$i,PdesColor,1) $couleurCourante(Arc)
    set tabTransition($tpn(courant),$i,label,nom) [genererUniqueTransId $i "T$i"]
    set tabTransition($tpn(courant),$i,id) "T$i"
    set tabTransition($tpn(courant),$i,label,dx) 25
    set tabTransition($tpn(courant),$i,label,dy) 0
    set tabTransition($tpn(courant),$i,guard,dx) 20
    set tabTransition($tpn(courant),$i,guard,dy) -20
    set tabTransition($tpn(courant),$i,update,dx) 20
    set tabTransition($tpn(courant),$i,update,dy) 10
    set tabTransition($tpn(courant),$i,speed,dx) -20
    set tabTransition($tpn(courant),$i,speed,dy) 5
    set tabTransition($tpn(courant),$i,cost,dx) -20
    set tabTransition($tpn(courant),$i,cost,dy) 5
    
    set tabTransition($tpn(courant),$i,cost) 0
    set tabTransition($tpn(courant),$i,speed) 1
    set tabTransition($tpn(courant),$i,priority) 0
    set tabTransition($tpn(courant),$i,dmin) 0
    set tabTransition($tpn(courant),$i,eftIncl) 1
    set tabTransition($tpn(courant),$i,lftIncl) 1
    set tabTransition($tpn(courant),$i,dmax) $infini
    set tabTransition($tpn(courant),$i,minparam) ""
    set tabTransition($tpn(courant),$i,maxparam) ""
    set tabTransition($tpn(courant),$i,obs) 1
    set tabTransition($tpn(courant),$i,unctrl) 0
    set tabTransition($tpn(courant),$i,update) ""
    set tabTransition($tpn(courant),$i,guard) ""
    set parikhVector($tpn(courant),$i) 0
    if {$creerTransition==-2} {
	  set eclair(transition) $i
      }
  

    redessinerRdP $c
set semExclusionElement 1
}
}

# ********************* SUPPRIMER TRANSITION ***********************
proc supprimerTransition  {numTransition} {
    global tabTransition 
    global tpn tabUnDo
    global destroy
    global modif
    global synchronized
    
    modifTPN $tpn(courant)
    set tabTransition($tpn(courant),$numTransition,statut) $destroy
    deleteTransInSynch $numTransition
}

# ********************* supprimer transition inutil car juste status destroy ***********************


#*******************************---- DOUBLE CLICK ----***********************************

# ***************** Double Click sur une place *****************

proc doubleClickP {c numPlace slave} {
    global semaphore 
    global plot
    global tabPlace 
    global tpn tabUnDo
    global nbProcesseur
    global resultat
    global nouveauNomP nouvelIdP boutonIdentifier
    global nbJeton
    global bornemin bornemax infini
    global modif
    global prio
    global typePN
    global francais
    global resultat
    global maxX maxY zoom
    global simulatorOn nbTokenColor
    global tabColor resultatCouleur couleurCourante

majcanvas $c $slave

      # semaphore(Release) : pour empecher releasePlace (dans manitag.tcl) de deplacer la place
      set semaphore(Release) 0
 if {$simulatorOn!=1} {
  if {![placeDansLaSelection $c $numPlace]} {


      set fp .fenetrePlace
      catch {destroy $fp}
      toplevel $fp 

      wm title $fp "Place Parameters"
	
      set deltaX [lindex [$c xview] 0]
      set x [expr int(($tabPlace($tpn(courant),$numPlace,xy,x)-$maxX*$deltaX)*$zoom +[winfo rootx $c]) -25]
      set deltaY [lindex [$c yview] 0]
      set y [expr int(($tabPlace($tpn(courant),$numPlace,xy,y)-$maxY*$deltaY)*$zoom+[winfo rooty $c]) - 25 ]

      set sw [winfo screenwidth $fp]
      set sh [winfo screenheight $fp]

      set x [expr {max(0, min($x, $sw-100))}]   ;# 100 = largeur fenÃªtre
      set y [expr {max(0, min($y, $sh-50))}]    ;# 50 = hauteur fenÃªtre
      wm geometry $fp +$x+$y
	
      label $fp.indice
      pack $fp.indice -side top
      $fp.indice config -text "Index : $numPlace"


      set nouveauNomP $tabPlace($tpn(courant),$numPlace,label,nom)
      set nouvelIdP $tabPlace($tpn(courant),$numPlace,id)
      set bornemin $tabPlace($tpn(courant),$numPlace,dmin)
      if {$tabPlace($tpn(courant),$numPlace,dmax) == $infini} {
	    set bornemax ""
      } else {
	    set bornemax $tabPlace($tpn(courant),$numPlace,dmax)
      }

	
      frame $fp.nom -bd 2
      entry $fp.nom.saisieNom -justify left -textvariable nouveauNomP -font menufont -relief sunken -width 40 -bg white 
      label $fp.nom.label
      pack $fp.nom.saisieNom -side right
      pack $fp.nom.label -side left
      $fp.nom.label config -text Label: -font menufont
	
      frame $fp.identifier -bd 2
      if {$boutonIdentifier} {
	  entry $fp.identifier.saisieId -justify left -textvariable nouveauNomP -font menufont -relief sunken -width 40 -bg white -state readonly
      } else {
	  entry $fp.identifier.saisieId -justify left -textvariable nouvelIdP -font menufont -relief sunken -width 40 -bg white -state normal
      }
      label $fp.identifier.label
      pack $fp.identifier.saisieId -side right
      pack $fp.identifier.label -side left
      $fp.identifier.label config -text Identifier: -font menufont


      bind $fp <Return> "validerP $c $fp $numPlace"


    checkbutton $fp.boutonidentifier -text "identifier <- label" -font menufont -variable boutonIdentifier \
	-relief flat -anchor w -selectcolor red -command "basculeIndentiferNomPlace $fp.identifier.saisieId"

#.control.frame.parametre.integer.hull.nofull configure -state active

      pack $fp.nom -side top -fill x
      pack  $fp.boutonidentifier -side top -pady 2 -anchor w
      label $fp.comment
      pack $fp.comment -side top -fill x
      $fp.comment config -text "(Identifier is unique and without space and start with a letter)" -font menufont
      pack $fp.identifier -side top -fill x
	
      set nbJeton $tabPlace($tpn(courant),$numPlace,jeton)
	
      frame $fp.jeton -bd 2
      entry $fp.jeton.saisieJeton -justify left -textvariable nbJeton -font menufont -relief sunken -width 10 -bg white
      label $fp.jeton.label
      pack $fp.jeton.label -side left
      pack $fp.jeton.saisieJeton -side left
      
      if {$nbTokenColor($tpn(courant)) >0} {
	  set leTexte ""
	  set coma ""
	  for {set i 0} {$i < $nbTokenColor($tpn(courant))}   {incr i} {
	      set leTexte "$leTexte$coma$i"
	      set coma ","
	  }
	  set leTexte "Colored marking, (ex: $leTexte ):"
      } else {
	  set leTexte "Token number:"
      }
      $fp.jeton.label config -text "$leTexte" -font menufont
	
      pack $fp.jeton -side top -fill x


# dmin dmax
        if {$typePN==2} {
	    frame $fp.noparam -relief ridge -bd 1 -height 2
	    pack $fp.noparam -side top

	    frame $fp.noparam.dmin -bd 2
	    entry $fp.noparam.dmin.saisieDmin -justify left -textvariable bornemin -font menufont -relief sunken -width 7 -bg white
	    label $fp.noparam.dmin.label
	    pack $fp.noparam.dmin.label -side left
	    pack $fp.noparam.dmin.saisieDmin -side left
	    $fp.noparam.dmin.label config -text "dmin:  " -font menufont
	
	    frame $fp.noparam.dmax -bd 2
	
	    label $fp.noparam.dmax.label
	    pack $fp.noparam.dmax.label -side left
	    $fp.noparam.dmax.label config -text "dmax:" -font menufont
	    pack $fp.noparam.dmin -side top -fill x
	    pack $fp.noparam.dmax -side top -fill x
	

            entry $fp.noparam.dmax.saisieDmax -justify left -textvariable bornemax -font menufont -relief sunken -width 10 -bg white

	    pack $fp.noparam.dmax.saisieDmax -side left

	    label $fp.noparam.dmax.infini
	    pack $fp.noparam.dmax.infini -side left
           $fp.noparam.dmax.infini config -text [mc "default: infinity"] -font menufont
	}
# SCHEDULING
	
	if {$typePN==-2} {
	    frame $fp.scheduling -relief ridge -bd 1 -height 2
	    pack $fp.scheduling -side left
	    label $fp.scheduling.label
	    pack $fp.scheduling.label -side top
	    if {$francais==1} {
		$fp.scheduling.label config -text "Extention à l'ordonnancement" -font menufont
	    } else {
		$fp.scheduling.label config -text "Scheduling extension" -font menufont
	    }
	    set prio $tabPlace($tpn(courant),$numPlace,priorite)
	    
	    frame $fp.scheduling.priorite -bd 2
	    entry $fp.scheduling.priorite.saisiepriorite -font menufont -justify left -textvariable prio -relief sunken -width 10 -bg white
	    label $fp.scheduling.priorite.label
	    pack $fp.scheduling.priorite.label -side left
	    pack $fp.scheduling.priorite.saisiepriorite -side left
	    if {$francais==1} {
		$fp.scheduling.priorite.label config -text "priorité :        " -font menufont
	    } else {
		$fp.scheduling.priorite.label config -text "priority :        " -font menufont
	    }
	    pack $fp.scheduling.priorite -side top -fill x
	    
	    frame $fp.scheduling.processeur
	    pack $fp.scheduling.processeur  -side left -expand yes -fill y  -pady .5c -padx .5c
	    
	    if {$francais==1} {
		label $fp.scheduling.processeur.label -text "Affectation de la place au processeur :" -font menufont
	    } else {
		label $fp.scheduling.processeur.label -text "processor (gamma):" -font menufont
	    }
	    frame $fp.scheduling.processeur.sep -relief ridge -bd 1 -height 2
	    pack $fp.scheduling.processeur.label -side top
	    pack $fp.scheduling.processeur.sep -side top -fill x -expand no
	    
	    set resultat $tabPlace($tpn(courant),$numPlace,processeur)
	    
	    for {set i 0} {$i <= $nbProcesseur($tpn(courant))}   {incr i} {
		if {$francais==1} {
		    if {$i==0} {set Processeur "sans affectation"} else {set Processeur "Processeur $i"}
		} else {
		    if {$i==0} {set Processeur "no"} else {set Processeur "Processor $i"}
		}
		radiobutton $fp.scheduling.processeur.b$i -text $Processeur -font menufont -variable resultat \
		    -relief flat  -value $i  -width 16 -anchor w -selectcolor red
		pack $fp.scheduling.processeur.b$i  -side top -pady 2 -anchor w -fill x
	    }
	} else {
	    set prio $tabPlace($tpn(courant),$numPlace,priorite)
	    set resultat $tabPlace($tpn(courant),$numPlace,processeur)
	}
	# si pas scheduling on maintient les valeurs (on pourait remettre à zero ?
	
	
	# Gestion des couleurs :
    frame $fp.color -bd 2
    pack $fp.color -side top
	label $fp.color.label
	pack $fp.color.label -side left
	$fp.color.label config -text "color:  " -font menufont
	    
    set resultatCouleur(Place) $tabPlace($tpn(courant),$numPlace,color)
    selectionCouleur $fp.color Place

	
	bind $fp <Return> "validerP $c $fp $numPlace"
	bind $fp <Escape> "destroy $fp"
	
	frame $fp.buttons
	pack $fp.buttons -side bottom -fill x -pady 2m
	if {$francais==1} {
	    button $fp.buttons.annuler -text Annuler -command  "destroy $fp"
	    button $fp.buttons.accepter -default active -text "Accepter"  -font menufont \
		-command "validerP $c $fp $numPlace"
	} else {
	    button $fp.buttons.annuler -text Cancel -font menufont -command  "destroy $fp"
	    button $fp.buttons.accepter -default active -text "  Ok  "  -font menufont \
		-command "validerP $c $fp $numPlace"
	}
	pack $fp.buttons.accepter $fp.buttons.annuler -side left -expand 1

  }	else {
  # si place dans la selection :  
  changerCouleurSelection $c
  }
 } 


 #fin si notsimulatoron 
 
    proc validerP {c fl numP} {
      global resultat
      global nouveauNomP nouvelIdP boutonIdentifier
      global tabPlace typePN
      global tpn tabUnDo
      global bornemin bornemax infini
      global nbJeton
      global modif
      global prio nbTokenColor
      global resultatCouleur couleurCourante

      set onContinue 1
	
      if {($typePN==-2)&&($resultat!=0)&&([incompatibleTransForScheduling $tpn(courant) $numP]>0)} {
	  set button [tk_messageBox -message "Transition [incompatibleTransForScheduling $tpn(courant) $numP] with 2 input scheduling Places"]
	  set onContinue 0
      } 
      if {$nbTokenColor($tpn(courant))<=0} {
	  set x [format %d $nbJeton]  
      } elseif  {[markingValide $nbJeton $nbTokenColor($tpn(courant))]==0} {
	  set onContinue 0
	  set button [tk_messageBox -message "Invalid colored marking"]
      }

      if {$onContinue} {
	  modifTPN $tpn(courant)

	 
	  set nouveauNomP [alphanumerique $nouveauNomP]
	  
	  if {[lsearch [list else if while for case switch return struct continue do static default int long double] $nouveauNomP]>=0} {
	      set nouveauNomP "P_$nouveauNomP"
	  }

	  if {$boutonIdentifier==1} {
	      set nouvelIdP $nouveauNomP
	  }

          if {[sansEspace $nouvelIdP] ==""} {set nouvelIdP "P$numP"}

		
	  set nouvelIdP [uneLettreaudebut [alphanumerique [genererUniquePlaceId $numP [sansEspace $nouvelIdP]]]]

# set nouveauNomP [retirerListeCar $nouveauNomP  [list < > ' / é è & # @ $ . _ , = % ! ?]]
#	  set nouveauNomP [join [split $nouveauNomP "_"] "-"]
#	  set nouveauNomP [sansEspace $nouveauNomP]

	set couleurCourante(Place) $resultatCouleur(Place)
	set tabPlace($tpn(courant),$numP,color) $resultatCouleur(Place)
	set tabPlace($tpn(courant),$numP,processeur) $resultat
	set tabPlace($tpn(courant),$numP,label,nom) $nouveauNomP
	set tabPlace($tpn(courant),$numP,id) $nouvelIdP
	set tabPlace($tpn(courant),$numP,jeton) $nbJeton
	set tabPlace($tpn(courant),$numP,priorite) $prio

	# if {$parameters==0} {	} A AJOUTER QUAND PARAMETRE AUSSI SUR PLACE
	if {$bornemax == ""} {set bornemax $infini}
	set x [format %d  $bornemin]
	set y [format %d $bornemax]
        if {($x <=0)} {set x 0}
	if {$y > $infini} {set y $infini}
	if {$x >= $y} {set x $y}
	if {$x >= $infini} {set x 0}
          
	set tabPlace($tpn(courant),$numP,dmin) $x
	set tabPlace($tpn(courant),$numP,dmax) $y

	
	#    set button [tk_messageBox -message "Selection \Processeur $resultat\" "]
	destroy $fl
	
	redessinerRdP $c
      }
    }

    
}


# ***************** Double Click sur une transition *****************

proc doubleClickT {c numTransition slave} {
    global semaphore 
    global plot
    global tabTransition 
    global tpn tabUnDo
    global bornemin bornemax includedmin includedmax
    global minp maxp
    global theSpeed theCost thePrio isCommitted
    global nouveauNom nouvelId boutonIdentifier
    global modif
    global francais
    global parameters synchronized typePN cost controle
    global infini
    global dmaxInfini
    global maxX maxY zoom
    global simulatorOn
    global tabColor resultatCouleur couleurCourante
    global estObservable estIncontrolable
    global avecDeveloppementEncours

majcanvas $c $slave


 set semaphore(Release) 0
    
 if {$simulatorOn==1} {
	simulatorFireTranstion $c $numTransition $slave
 } else {
  if {![transitionDansLaSelection $c $numTransition]} {

	set nouveauNom $tabTransition($tpn(courant),$numTransition,label,nom)
	set nouvelId $tabTransition($tpn(courant),$numTransition,id)

	set includedmin $tabTransition($tpn(courant),$numTransition,eftIncl)
	set includedmax $tabTransition($tpn(courant),$numTransition,lftIncl)
	set bornemin $tabTransition($tpn(courant),$numTransition,dmin)
	set bornemax $tabTransition($tpn(courant),$numTransition,dmax)
	set theSpeed $tabTransition($tpn(courant),$numTransition,speed)
	set thePrio $tabTransition($tpn(courant),$numTransition,priority)
	if ($thePrio!=0) {
	    set isCommitted 1
	    set etatSaisieTempo normal
	} else {
	    set isCommitted 0
	    set etatSaisieTempo normal
	}

	set theCost $tabTransition($tpn(courant),$numTransition,cost)
	
	set f .fenetreTransition
	catch {destroy $f}
	toplevel $f
	
	set deltaX [lindex [$c xview] 0]
	set x [expr int(($tabTransition($tpn(courant),$numTransition,xy,x)-$maxX*$deltaX)*$zoom +[winfo rootx $c]) - 20]
	set deltaY [lindex [$c yview] 0]
	set y [expr int(($tabTransition($tpn(courant),$numTransition,xy,y)-$maxY*$deltaY)*$zoom +[winfo rooty $c]) - 250]

     set sw [winfo screenwidth $f]
      set sh [winfo screenheight $f]

      set x [expr {max(0, min($x, $sw-100))}]   ;# 100 = largeur fenÃªtre
      set y [expr {max(0, min($y, $sh-50))}]    ;# 50 = hauteur fenÃªtre
      wm geometry $f +$x+$y
	
 
    wm title $f "Transition parameters"
	

	label $f.indice
	pack $f.indice -side top
	$f.indice config -text "Index : $numTransition" -font menufont
	frame $f.nom -bd 2
	entry $f.nom.saisieNom -justify left -textvariable nouveauNom -font menufont -relief sunken -width 40 -bg white
	label $f.nom.label
	pack $f.nom.saisieNom -side right
	pack $f.nom.label -side left
	$f.nom.label config -text Label: -font menufont

     frame $f.identifier -bd 2

#	if {$boutonIdentifier==1} {
#	      set nouvelId $nouveauNom
#	}
#
 #       if {[sansEspace $nouvelId] ==""} {set nouvelId "T$numT"}
  #      set nouvelId [uneLettreaudebut [alphanumerique  [genererUniqueTransId $numT [sansEspace $nouvelId]]]]


      if {$boutonIdentifier} {
	  set nouvelId [sansEspace $nouveauNom]
	  entry $f.identifier.saisieId -justify left -textvariable nouveauNom -font menufont -relief sunken -width 40 -bg white -state readonly
      } else {
	  entry $f.identifier.saisieId -justify left -textvariable nouvelId -font menufont -relief sunken -width 40 -bg white -state normal
      }
      label $f.identifier.label
      pack $f.identifier.saisieId -side right
      pack $f.identifier.label -side left
      $f.identifier.label config -text Identifier: -font menufont


    checkbutton $f.boutonidentifier -text "identifier <- label" -font menufont -variable boutonIdentifier \
	-relief flat -anchor w -selectcolor red -command "basculeIndentiferNomTransition $f.identifier.saisieId"

      pack $f.nom -side top -fill x
      pack $f.boutonidentifier -side top -pady 2 -anchor w

      label $f.comment
      pack $f.comment -side top -fill x
      $f.comment config -text "(Identifier is unique and without space and start with a letter)" -font menufont
      pack $f.identifier -side top -fill x



# ***************** IL SUFFIRA DE DECOMMENTER CETTE PARTIE POUR LA SYNCHRO ********************

#	frame $f.synchro  -relief ridge -bd 2
#	label $f.synchro.titre
#	pack $f.synchro.titre -side top
#        $f.synchro.titre config -text "Synchronization (given by index)"
#        label $f.synchro.etat
#	pack $f.synchro.etat -side left
#	if {[isSynchronized $numTransition]} {
#	    $f.synchro.etat config -text [fonctionSynchro $synchronized $numTransition]
#	} else {
#	     $f.synchro.etat config -text "no synchronization"
#	}    
# 	button $f.synchro.define -text [mc "define"] -command  "defineSynchro $f  $numTransition"
# 	pack $f.synchro.define -side right
#	pack $f.synchro -side top -fill x
# fin de la partie à decommenter

# OBSERVABLE :

#        set estObservable  $tabTransition($tpn(courant),$numTransition,obs)
	set estObservable 1

        set estIncontrolable $tabTransition($tpn(courant),$numTransition,unctrl)

	if {($controle>1)&&($estIncontrolable>1)} { set estIncontrolable 1}


	
      pack $f.nom -side top -fill x
      pack $f.boutonidentifier -side top -pady 2 -anchor w

if {$controle>=1} {

	frame $f.crtl -relief ridge -bd 2
	pack $f.crtl -side top -fill x

 #       checkbutton $f.crtlobs.boutonObs -text "Observable transition"  -variable estObservable -selectcolor red \
#	      -relief flat  -width 10 -anchor w 
 #       pack $f.crtlobs.boutoObsn -side top -fill x

	frame $f.crtl.top  -bd 2
	pack $f.crtl.top -side top -fill x
	frame $f.crtl.top.left  -bd 2
	pack $f.crtl.top.left -side left -fill x
	frame $f.crtl.top.right   -bd 2
	pack $f.crtl.top.right -side left -fill x
	frame $f.crtl.bot   -bd 2
	pack $f.crtl.bot -side bottom -fill x
	
   radiobutton  $f.crtl.top.left.cont -text "Controlable" -font menufont -variable estIncontrolable -value 0 -selectcolor red 
   radiobutton  $f.crtl.top.right.uncont -text "Uncontrolable" -font menufont -variable estIncontrolable -value 1 -selectcolor red 
   pack $f.crtl.top.left.cont -side top -pady 2 -anchor w
   pack $f.crtl.top.right.uncont -side top -pady 2 -anchor w

   if {$controle==1} {  # A changer en ==1
     radiobutton  $f.crtl.top.left.uncontAvo -text "Uncontrolable and avoidable" -font menufont -variable estIncontrolable -value 2 -selectcolor red 
     radiobutton  $f.crtl.top.right.uncontIne -text "Uncontrolable and ineluctable" -font menufont -variable estIncontrolable -value 3 -selectcolor red 
     radiobutton  $f.crtl.bot.uncontAvoIne -text "Uncontrolable and avoidable and ineluctable" -font menufont -variable estIncontrolable -value 4 -selectcolor red 
#    radiobutton $s.parametre.paramUnder -text "Integer-preserving underapproximation" -font menufont -variable parameters -value 3 -selectcolor red -command "validParametre $w $c"
      pack $f.crtl.top.left.uncontAvo -side top -pady 2 -anchor w
      pack $f.crtl.top.right.uncontIne -side top -pady 2 -anchor w
      pack $f.crtl.bot.uncontAvoIne -side left -pady 2 -anchor w
   }

  }

# RAPPEL typePN :   -1 : stopwatch ;   -2 scheduling ; 1 t-tpn ; 2 p-tpn
# NO P-TPN (donc tempo ou parametre sur transition)
	if {($typePN!=2)} {
# NO PARAMETERS -- si par erreur il y a scheduling (-2) ou hybrid (-3) et parametre, on ne prend pas les parametres
         if {($parameters==0)} {
	    frame $f.noparam -relief ridge -bd 1 -height 2
	    pack $f.noparam -side top

	    frame $f.noparam.dmin -bd 2
	    entry $f.noparam.dmin.saisieDmin -justify left -textvariable bornemin -font menufont -relief sunken -width 7 -bg white -state $etatSaisieTempo
	    label $f.noparam.dmin.label
	    pack $f.noparam.dmin.label -side left
	    pack $f.noparam.dmin.saisieDmin -side left
	    $f.noparam.dmin.label config -text "dmin:  " -font menufont

	    checkbutton $f.noparam.dmin.inclmin -text "Incl." -variable includedmin -font menufont -selectcolor red \
	      -relief flat  -width 10 -anchor w 
	    pack $f.noparam.dmin.inclmin -side left

	    frame $f.noparam.dmax -bd 2
  	    frame $f.noparam.dmax.resultat -bd 2
	
	    label $f.noparam.dmax.label
	    pack $f.noparam.dmax.label -side left
	    $f.noparam.dmax.label config -text "dmax:" -font menufont
	    pack $f.noparam.dmin -side top -fill x
	    pack $f.noparam.dmax -side top -fill x


	     
	    if {$bornemax == $infini} {
	      set dmaxInfini 1
	      entry $f.noparam.dmax.resultat.saisieDmax -justify left -textvariable rien -font menufont -relief sunken -width 10 \
	     -bg white	-state disabled 
	    } else {
	      set dmaxInfini 0
	      entry $f.noparam.dmax.resultat.saisieDmax -justify left -textvariable bornemax -font menufont -relief sunken -width 10 -bg white -state $etatSaisieTempo
	    }
	
	    pack $f.noparam.dmax.resultat.saisieDmax -side left

	     if ($dmaxInfini==0) {
		 checkbutton $f.noparam.dmax.resultat.inclmax -text "Incl."  -variable includedmax -font menufont -selectcolor red \
		     -relief flat  -width 10 -anchor w -state active
	     } else {
		 checkbutton $f.noparam.dmax.resultat.inclmax -text "Incl."  -variable includedmax -font menufont -selectcolor red \
		     -relief flat  -width 10 -anchor w -state disabled 
	     }

	     
	    checkbutton $f.noparam.dmax.resultat.infini -text "Infinity"  -variable dmaxInfini -font menufont -selectcolor red \
	      -relief flat  -width 10 -anchor w -command  "borneMaxInfini $f.noparam.dmax.resultat"
	
	    pack $f.noparam.dmax.resultat.inclmax -side top
	    pack $f.noparam.dmax.resultat.infini -side bottom -pady 2 -anchor w -fill x
	    pack $f.noparam.dmax.resultat -side left
	    set minp $tabTransition($tpn(courant),$numTransition,minparam)
	    set maxp $tabTransition($tpn(courant),$numTransition,maxparam)

	     frame $f.committed -bd 2
#	     if ($thePrio!=0) {set isCommitted 1}
	     checkbutton $f.committed.boutonCommitted -text "Committed Transition with priority:" -font menufont  -variable isCommitted \
		-relief flat -anchor w -selectcolor red -command "basculeCommitted $f.noparam $f.committed 0"
	     if ($thePrio!=0) {
		 entry $f.committed.saisiePrio -justify left -textvariable thePrio -font menufont -relief sunken -width 4 -bg white  \
		    -state normal
	     } else {
		 entry $f.committed.saisiePrio -justify left -textvariable thePrio -font menufont -relief sunken -width 4 -bg white  \
		    -state disabled
	     }
	     pack $f.committed -side top -fill x
	     pack $f.committed.boutonCommitted -side left -fill x
	     pack $f.committed.saisiePrio -side left -fill x
# PARAMETERS 
 	  } else {
	    frame $f.parameterized -relief ridge -bd 1 -height 2
	    pack $f.parameterized -side top
	    label $f.parameterized.label
	    pack $f.parameterized.label -side top
            $f.parameterized.label config -text [mc "Parametric Extension"] -font menufont

	    set minp $tabTransition($tpn(courant),$numTransition,minparam)
	    set maxp $tabTransition($tpn(courant),$numTransition,maxparam)
	    
	    frame $f.parameterized.minparam -bd 2
	    entry $f.parameterized.minparam.saisiemin -justify left -textvariable minp -font menufont -relief sunken -width 10 -bg white -state $etatSaisieTempo
	    label $f.parameterized.minparam.label
	    pack $f.parameterized.minparam.label -side left
	    pack $f.parameterized.minparam.saisiemin -side left
	    $f.parameterized.minparam.label config -text "Min param:        " -font menufont

	      
	    checkbutton $f.parameterized.minparam.inclmin -text "Incl." -variable includedmin -font menufont -selectcolor red \
	      -relief flat  -width 10 -anchor w 
	    pack $f.parameterized.minparam.inclmin -side top

	    label $f.parameterized.minparam.infini
	    pack $f.parameterized.minparam.infini -side left
            $f.parameterized.minparam.infini config -text [mc "default: 0"] -font menufont

	    pack $f.parameterized.minparam -side top -fill x

	      

	      

	    frame $f.parameterized.maxparam -bd 2
	    label $f.parameterized.maxparam.label
	    pack $f.parameterized.maxparam.label -side left

            entry $f.parameterized.maxparam.saisieDmax -justify left -textvariable maxp -font menufont -relief sunken -width 10 -bg white -state $etatSaisieTempo
	
	    pack $f.parameterized.maxparam.saisieDmax -side left
	    $f.parameterized.maxparam.label config -text "Max param:        " -font menufont

	      
	    label $f.parameterized.maxparam.infini
	    pack $f.parameterized.maxparam.infini -side bottom
            $f.parameterized.maxparam.infini config -text [mc "default: infinity"] -font menufont
	    pack $f.parameterized.maxparam -side top -fill x

	     checkbutton $f.parameterized.maxparam.inclmax -text "Incl." -font menufont -variable includedmax -selectcolor red \
	      -relief flat  -width 10 -anchor w 
	      pack $f.parameterized.maxparam.inclmax -side top
	      
	     frame $f.committed -bd 2
#	     if ($thePrio!=0) {set isCommitted 1}
	     checkbutton $f.committed.boutonCommitted -text "Committed Transition with priority:" -font menufont  -variable isCommitted \
		-relief flat -anchor w -selectcolor red -command "basculeCommitted  $f.parameterized $f.committed 1"
	     if ($thePrio!=0) {
		 entry $f.committed.saisiePrio -justify left -textvariable thePrio -relief sunken -width 4 -bg white \
		    -state normal
	     } else {
		 entry $f.committed.saisiePrio -justify left -textvariable thePrio -font menufont -relief sunken -width 4 -bg white  \
		    -state disabled
	     }
	     pack $f.committed -side top -fill x
	     pack $f.committed.boutonCommitted -side left -fill x
	      pack $f.committed.saisiePrio -side left -fill x

	      
	      
#	      checkbutton $f.boutonCommitted -text "Committed Transition"  -variable thePrio \
#		-relief flat -anchor w -selectcolor red -command "basculeCommitted $f.parameterized glop 1 "
#	     pack $f.boutonCommitted -side top -fill x
	  }

	}

#------  et en plus il y a le speed pour les hybrid-t-tpn
	if {($typePN==-3)} {
		 frame $f.hybrid -relief ridge -bd 1 -height 2
		 pack $f.hybrid -side top

		 frame $f.hybrid.speed -bd 2
		 entry $f.hybrid.saisieSpeed -justify left -textvariable theSpeed -font menufont -relief sunken -width 22 -bg white
		 label $f.hybrid.label
		 pack $f.hybrid.label -side left
		 pack $f.hybrid.saisieSpeed -side left
		 $f.hybrid.label config -text "Speed (d\/dt):  " -font menufont

	}



#------  et en plus il y a le cost  
	if {($cost>0)} {
		 frame $f.cost -relief ridge -bd 1 -height 2
		 pack $f.cost -side top

		 frame $f.cost.tweight -bd 2
		 entry $f.cost.saisieCost -justify left -textvariable theCost -font menufont -relief sunken -width 22 -bg white
		 label $f.cost.label
		 pack $f.cost.label -side left
		 pack $f.cost.saisieCost -side left
		 $f.cost.label config -text "Discrete Cost:  " -font menufont

	}

#------------------GUARD

	frame $f.guard -relief ridge -bd 2
	pack $f.guard -side top
	label $f.guard.label
	pack  $f.guard.label -side left
	 $f.guard.label config -text "Guard:  " -font menufont

	text $f.guard.text -yscrollcommand "$f.guard.scroll set"  -setgrid true -font menufont \
-width 30 -height 3 -wrap word -bg white 
	scrollbar $f.guard.scroll -command "$f.guard.text yview" 

	pack $f.guard.scroll -side right -fill y 
	pack $f.guard.text -expand yes -fill both 

	$f.guard.text insert end $tabTransition($tpn(courant),$numTransition,guard)


#------------------UPDATE

	frame $f.code -relief ridge -bd 2
	pack $f.code -side top
	label $f.code.label
	pack  $f.code.label -side left
	 $f.code.label config -text "Update:  " -font menufont

	text $f.code.text -yscrollcommand "$f.code.scroll set" -setgrid true -font menufont \
-width 30 -height 4 -wrap word -bg white 
	scrollbar $f.code.scroll -command "$f.code.text yview" 

	pack $f.code.scroll -side right -fill y 
	pack $f.code.text -expand yes -fill both 

	$f.code.text insert end $tabTransition($tpn(courant),$numTransition,update) 




	set resultatCouleur(Transition) $tabTransition($tpn(courant),$numTransition,color)
       if {$controle!=1} {


# Gestion des couleurs :
	frame $f.color -bd 2
	pack $f.color -side top
	label $f.color.label
	pack $f.color.label -side left
	$f.color.label config -text "color:  " -font menufont
	    
	set resultatCouleur(Transition) $tabTransition($tpn(courant),$numTransition,color)
	selectionCouleur $f.color Transition

    }
	
#	bind $f <Return> "validerT $c $f $numTransition"
#	bind $f <Escape> "destroy $f"
	frame $f.buttons
	pack $f.buttons -side bottom -fill x -pady 2m
	if {$francais==1} {
	    button $f.buttons.annuler -text Annuler -font menufont -command  "destroy $f"
	    button $f.buttons.aide  -text " Aide " -font menufont -command "helpTransition $f"
	    button $f.buttons.accepter -text "Accepter"  -font menufont \
		-command "validerT $c $f $numTransition"
	} else {
	    button $f.buttons.annuler -text Cancel -font menufont -command  "destroy $f"
	    button $f.buttons.aide  -text " Help " -font menufont -command "helpTransition $f"
	    button $f.buttons.accepter  -text "  Ok  " -font menufont \
		-command "validerT $c $f $numTransition"
	}
	pack $f.buttons.accepter $f.buttons.aide $f.buttons.annuler  -side left -expand 1
 } else {
 #si transition dans la selection
 changerCouleurSelection $c
 }
 } 
  
   
    #++++++ procedures internes à doubleClickT
   proc helpTransition  {fT} {
global parameters
	set fhelp $fT.help
	catch {destroy $fhelp}
	toplevel $fhelp

       text $fhelp.syntax -yscrollcommand "$fhelp.vscroll set" -width 70 -height 27 -bg white -wrap word -font fontEditor
       pack $fhelp.syntax -side left -fill both -expand yes
       scrollbar $fhelp.vscroll -command "$fhelp.syntax yview"
       pack $fhelp.syntax -side left -fill both -expand yes
       pack $fhelp.vscroll -side right -fill y
       

       $fhelp.syntax tag configure maron -foreground brown
       $fhelp.syntax tag configure rouge -foreground red
       $fhelp.syntax tag configure vert -foreground darkgreen
       $fhelp.syntax tag configure bleu -foreground darkblue
       $fhelp.syntax tag configure surgris -background #c0d7ee

       $fhelp.syntax insert end "Linear expression over a set X =" surgris
       $fhelp.syntax insert end "  a*x  \| p op q   " bleu
       $fhelp.syntax insert end " where \n"
       $fhelp.syntax insert end "  x    " rouge
       $fhelp.syntax insert end " is in X ; \n" 
       $fhelp.syntax insert end "  a    " rouge
       $fhelp.syntax insert end " is a positive or negative integer coefficient ; \n" 
       $fhelp.syntax insert end "  op   " rouge
       $fhelp.syntax insert end " is in \{+,-\} ; \n" 
       $fhelp.syntax insert end "  p,q  " rouge
       $fhelp.syntax insert end " are linear expressions over X ;\n \n"

	if {$parameters>=1} {
#	    $fhelp.syntax insert end "A Parametric Timed Constraint of a transition is a linear expression over the set Par of parameters \n"
	    $fhelp.syntax insert end "\[Min param, Max param\]" surgris
	    $fhelp.syntax insert end " is the timed firing interval of the transition:\n"
	    $fhelp.syntax insert end "Min param" rouge
	    $fhelp.syntax insert end " is a linear expression over the set "
	    $fhelp.syntax insert end "Par" bleu
	    $fhelp.syntax insert end " of parameters\n"
	    $fhelp.syntax insert end "Max param" rouge
	    $fhelp.syntax insert end " is either  a linear expression over "
	    $fhelp.syntax insert end "Par" bleu
	    $fhelp.syntax insert end " or infinity\n\n"
	    $fhelp.syntax insert end "-------------------------------------------------------\n" bleu
	}


       $fhelp.syntax insert end "Let X the set of variables declared in the " 
       $fhelp.syntax insert end "Declaration" surgris
       $fhelp.syntax insert end " bloc of the Petri Net Tab:  \n "
       $fhelp.syntax insert end "initially \{...X declaration and initialization ..\}" bleu
       $fhelp.syntax insert end " \n \n Guard and Update of transition must be of the form: \n\n"

       $fhelp.syntax insert end "Guard =" surgris
       $fhelp.syntax insert end "  lexp ~ k \|  op1 p \| p op2 q  " bleu 
       $fhelp.syntax insert end " with \n"
       $fhelp.syntax insert end "  lexp" rouge
       $fhelp.syntax insert end "  is a linear expression over X  \n" 
       $fhelp.syntax insert end "  k    " rouge
       $fhelp.syntax insert end " is positive or negative integer ; \n" 
       $fhelp.syntax insert end "  ~    " rouge
       $fhelp.syntax insert end " is a comparison operator in \{<,<=, >, >=, ==\} ; \n" 
       $fhelp.syntax insert end "  op1  " rouge
       $fhelp.syntax insert end " is the logical negation operator in \{not, !\} ; \n" 
       $fhelp.syntax insert end "  op2  " rouge
       $fhelp.syntax insert end " is a logical operator in \{and, \&\&, or, \|\|\} ; \n" 
       $fhelp.syntax insert end "  p,q  " rouge
       $fhelp.syntax insert end " are guards ; \n\n"

       $fhelp.syntax insert end "Example: x < 3 and x-2*y==4 and 3*x+z>=8 \n" vert
       $fhelp.syntax insert end "If x=-2, y=-3 and z =20 then the guard is true\n\n\n"


 #      $fhelp.syntax insert end " An update of a transition must be of the form: \n\n"
       $fhelp.syntax insert end "Update =" surgris
       $fhelp.syntax insert end "  x = f ; \| x = g ;  \| p q   " bleu
       $fhelp.syntax insert end " with \n"
       $fhelp.syntax insert end "  x    " rouge
       $fhelp.syntax insert end " is a variable in X ; \n" 
       $fhelp.syntax insert end "  f    " rouge
       $fhelp.syntax insert end " is a linear expression over the set X ; \n" 
       $fhelp.syntax insert end "  g    " rouge
       $fhelp.syntax insert end " is a function declared in the "
       $fhelp.syntax insert end "Declaration" surgris
       $fhelp.syntax insert end " bloc ; \n" 
       $fhelp.syntax insert end "  p,q  " rouge
       $fhelp.syntax insert end " are updates ;\n \n"
       $fhelp.syntax insert end "Note that the updates p and q will be executed sequentially : p before q. \n\n" 
       $fhelp.syntax insert end "Example: " vert
       $fhelp.syntax insert end "Assuming x,y,z are integer variables and f is the Square Function: f(x) = x^2. Let T, a transition with the following update : \n"
       $fhelp.syntax insert end "     x = 3 ; \n     y=f(x) ;\n     z = x-2 ; \n" vert
       $fhelp.syntax insert end " The firing of the transition T will return x=3, y=9 and z=1." 
 

   }

    proc validerT {c fl numT} {
	global resultat
	global nouveauNom nouvelId boutonIdentifier
	global bornemin theSpeed theCost thePrio isCommitted
	global includedmin includedmax
	global bornemax estObservable estIncontrolable
    	global minp
    	global maxp 
	global tabTransition 
	global tpn tabUnDo
	global modif
	global infini parameters
        global resultatCouleur couleurCourante
		

	modifTPN $tpn(courant)

	set lagarde [$fl.guard.text get 1.0 {end -1c}]
	set lupdate [$fl.code.text get 1.0 {end -1c}]

        if {[sansEspace $lagarde] ==""} {set lagarde ""}

	set erreurUpdate [verifSyntaxeUpdate $lupdate]
#	set erreurUpdate ""
	set erreurGarde [verifSyntaxeGarde $lagarde]

	if {$erreurGarde!= ""} {
	  set button [tk_messageBox -icon warning -type ok -message  "Syntax Error in guard $lagarde : \n $erreurGarde"]
	} elseif {$erreurUpdate!= ""} {
	  set button [tk_messageBox -icon warning -type ok -message  "Syntax Error in update : \n $erreurUpdate"]
	} 
	set couleurCourante(Transition) $resultatCouleur(Transition)
	set tabTransition($tpn(courant),$numT,color) $resultatCouleur(Transition)
	set tabTransition($tpn(courant),$numT,obs) $estObservable
	set tabTransition($tpn(courant),$numT,unctrl) $estIncontrolable


        if {$theSpeed == ""} {
	    set theSpeed 1
	}
	set tabTransition($tpn(courant),$numT,speed) $theSpeed
	set tabTransition($tpn(courant),$numT,priority) $thePrio

       if {![catch  {set theCostOk [format %d  $theCost]}]} {
           set tabTransition($tpn(courant),$numT,cost) $theCostOk
        } else {
            if {[sansEspace $theCost]==""} {
		 set theCost 0
	    }
#else {
#		tk_messageBox -message "Make sure that $theCost is an integer " -icon warning
#	    }
	    set tabTransition($tpn(courant),$numT,cost) $theCost 
           #    set reponse [tk_messageBox -message "$theCost mst be integer"] -type yesnocancel -icon question] 
        }


	set  tabTransition($tpn(courant),$numT,update) $lupdate
	set  tabTransition($tpn(courant),$numT,guard) $lagarde


#	set nouveauNom [retirerListeCar $nouveauNom  [list < > / ' é è & # @ $ . , = % ! ?]]
#	set nouveauNom [join [split $nouveauNom "_"] "-"]
#	set nouveauNom [sansEspace $nouveauNom]
        set nouveauNom [alphanumerique $nouveauNom]

        if {[lsearch [list else if while for case switch return struct continue do static default int long double] $nouveauNom]>=0} {
            set nouveauNom "T_$nouveauNom"
        }

	if {$boutonIdentifier==1} {
	      set nouvelId $nouveauNom
	}

        if {[sansEspace $nouvelId] ==""} {set nouvelId "T$numT"}
        set nouvelId [uneLettreaudebut [alphanumerique  [genererUniqueTransId $numT [sansEspace $nouvelId]]]]

     if {$parameters==0} {	
        set bornemin [format %d  $bornemin]
        set bornemax [format %d $bornemax]
        if {($bornemin>$bornemax)||($thePrio>0)} {
	    set bornemax $bornemin
	    set includedmin 1
	    set includedmax 1
	}
        if {($includedmin==0)||($includedmax==0)} {
            if {($bornemin==$bornemax)} {
	       set bornemax [expr $bornemax+1]
            }
	}
        if {$bornemax >= $infini} {set includedmax 0}
    
	if {[expr ($bornemin <= $bornemax)&&($bornemin >=0)]} {
            if {$bornemax > $infini} {set bornemax $infini}
   	    set tabTransition($tpn(courant),$numT,dmin) $bornemin
	    set tabTransition($tpn(courant),$numT,dmax) $bornemax
   	    set tabTransition($tpn(courant),$numT,eftIncl) $includedmin
   	    set tabTransition($tpn(courant),$numT,lftIncl) $includedmax
	    set tabTransition($tpn(courant),$numT,label,nom) $nouveauNom
	    set tabTransition($tpn(courant),$numT,id) $nouvelId

	    destroy $fl
	    redessinerRdP $c
	    
	} else {
	    set button [tk_messageBox -message "Not allowed : Transition $nouveauNom \n \[ $bornemin ; $bornemax \]"]
	}
    } else {  # cad si parameters>=1  ICI il faudra verifier que l'expression est correct a op b avec op in (+,_)
      set minp [retirerListeCar $minp  [list < > & # @ $ . , = % ! ?]]
      set maxp [retirerListeCar $maxp  [list < > & # @ $ . , = % ! ?]]
      if {([sansEspace $maxp]=="infinity")||([sansEspace $maxp]=="inf")} {set maxp ""}
      if {[sansEspace $minp]==""} { set minp 0}
      if {$thePrio>0} {set maxp $minp}
      if {([verifSyntaxeParametre $minp]=="")&&([verifSyntaxeParametre $maxp]=="")} {
	  set tabTransition($tpn(courant),$numT,minparam) [gotonext $minp]
	  set tabTransition($tpn(courant),$numT,maxparam) [gotonext $maxp]
	  set tabTransition($tpn(courant),$numT,eftIncl) $includedmin
	  set tabTransition($tpn(courant),$numT,lftIncl) $includedmax

         set tabTransition($tpn(courant),$numT,label,nom) $nouveauNom
	 set tabTransition($tpn(courant),$numT,id) $nouvelId
	 if {[entier [sansEspace $tabTransition($tpn(courant),$numT,minparam)]]} {
	     set tabTransition($tpn(courant),$numT,minparam) [sansEspace $tabTransition($tpn(courant),$numT,minparam)]
         }
	 if {[entier [sansEspace $tabTransition($tpn(courant),$numT,maxparam)]]} {
	     set tabTransition($tpn(courant),$numT,maxparam) [sansEspace $tabTransition($tpn(courant),$numT,maxparam)]
         }
	 if {[entier $tabTransition($tpn(courant),$numT,minparam)]&&[entier $tabTransition($tpn(courant),$numT,maxparam)]} {
	     if {$tabTransition($tpn(courant),$numT,minparam) > $tabTransition($tpn(courant),$numT,maxparam)} {
		 set tabTransition($tpn(courant),$numT,maxparam) $tabTransition($tpn(courant),$numT,minparam)
	     }
	     if {$tabTransition($tpn(courant),$numT,minparam) == $tabTransition($tpn(courant),$numT,maxparam)} {
		 set tabTransition($tpn(courant),$numT,eftIncl) "1"
		 set tabTransition($tpn(courant),$numT,lftIncl) "1"
	     }
	 }
         destroy $fl
         redessinerRdP $c
      } else { 
	  set button [tk_messageBox -icon error -message  "Parametric constraints \[$minp,$maxp\] \n [verifSyntaxeParametre $minp] [verifSyntaxeParametre $maxp]"]
      }
    }
    }
    

 proc basculeCommitted {chemin bouton param} {
 	global thePrio isCommitted
        global bornemin bornemax includedmin includedmax
	global dmaxInfini maxp
	global infini
 	global minp maxp
    	  	
#	destroy $inf.infini
#	destroy $inf.saisieDmax

     if ($param==0) {
        if {$isCommitted > 0} {
	   if ($thePrio==0) {set thePrio 1}
	   $bouton.saisiePrio configure -state normal
	    if {$bornemin!=$bornemax} {set bornemax $bornemin}
#	    set bornemin 0
#           set bornemax 0
           set dmaxInfini 0
    #       $chemin.dmin.saisieDmin  configure -state disabled 
 #          $chemin.dmax.resultat.saisieDmax  configure -state disabled
  #         $chemin.dmax.resultat.infini configure -state disabled
        } else {
	   set thePrio 0
	   $bouton.saisiePrio configure -state disabled
   #        $chemin.dmin.saisieDmin  configure -state normal 
    #       $chemin.dmax.resultat.saisieDmax  configure -textvariable bornemax -state normal
    #       $chemin.dmax.resultat.infini configure  -state normal
        }
   } else {
      if {$isCommitted > 0} {
	   if ($thePrio==0) {set thePrio 1}
	   $bouton.saisiePrio configure -state normal
	    if {$minp!=$maxp} {set maxp $minp}
#           set minp 0
#           set maxp 0
           set dmaxInfini 0
#           $chemin.minparam.saisiemin  configure -state disabled 
#           $chemin.maxparam.saisieDmax configure -state disabled
#           $chemin.dmax.resultat.infini configure -state disabled
      } else {
	  set thePrio 0
	  $bouton.saisiePrio configure -state disabled
#	  $chemin.minparam.saisiemin  configure -state normal 
#	  $chemin.maxparam.saisieDmax configure -state normal
	  #        $chemin.dmax.resultat.infini configure  -state normal
      }



   }

}

    proc borneMaxInfini {inf} {
 	global parameters
	global bornemin bornemax includedmin includedmax thePrio
	global dmaxInfini minp maxp
	global infini rien
	

	if {($thePrio==0)} {
 # 	  destroy $inf.infini
#        destroy $inf.saisieDmax
set rien ""

          if {($dmaxInfini == 1)} {
	      set bornemax $infini
	      $inf.saisieDmax configure -textvariable rien -state disabled
	      $inf.inclmax configure -state disabled

	  } else {
	     set bornemax $bornemin
	       $inf.saisieDmax configure -textvariable bornemax -state normal 
 	      $inf.inclmax configure -state active
	  }


#	checkbutton $inf.infini -text "infinity"  -variable dmaxInfini -selectcolor red \
#	    -relief flat  -width 10 -anchor w -command  "borneMaxInfini $inf"
	
#	pack $inf.infini -side bottom -pady 2 -anchor w -fill x
        }

	


#	pack $inf -side left
    }

   
}
# fin doubleClick


proc basculeIndentiferNomPlace {chemin} {
global boutonIdentifier nouveauNomP nouvelIdP

    if {$boutonIdentifier} {
       $chemin configure -state readonly -textvariable nouveauNomP
    } else {
	set nouvelIdP [uneLettreaudebut [alphanumerique $nouveauNomP]]
       $chemin configure -state normal -textvariable nouvelIdP
    }
}

proc basculeIndentiferNomTransition {chemin} {
global boutonIdentifier nouveauNom nouvelId

    if {$boutonIdentifier} {
       $chemin configure -state readonly -textvariable nouveauNom
    } else {
	set nouvelIdP [uneLettreaudebut [alphanumerique $nouveauNom]]
       $chemin configure -state normal -textvariable nouvelId
    }
}


# ************************ REORDONNER TABLEAU PLACE ET TRANSITION **************************


proc toutCommeYFaut  {} {
    global tabPlace
    global tabTransition 
    global tpn tabUnDo
    global fin
    global ok
    global destroy
    
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin} {incr i} {
	if {$tabTransition($tpn(courant),$i,statut)==$destroy} {
	    for {set j $i} {$tabTransition($tpn(courant),$j,statut)!=$fin} {incr j} {
		set tabTransition($tpn(courant),$j,statut) $tabTransition($tpn(courant),[expr $j+1],statut)
		if {$tabTransition($tpn(courant),[expr $j+1],statut)==$ok} {
		    set tabTransition($tpn(courant),$j,xy,x) $tabTransition($tpn(courant),[expr $j+1],xy,x)
		    set tabTransition($tpn(courant),$j,xy,y) $tabTransition($tpn(courant),[expr $j+1],xy,y)
		    set tabTransition($tpn(courant),$j,label,nom) $tabTransition($tpn(courant),[expr $j+1],label,nom)
		    set tabTransition($tpn(courant),$j,id) $tabTransition($tpn(courant),[expr $j+1],id)
		    set tabTransition($tpn(courant),$j,label,dx) $tabTransition($tpn(courant),[expr $j+1],label,dx)
		    set tabTransition($tpn(courant),$j,label,dy) $tabTransition($tpn(courant),[expr $j+1],label,dy)
		    set tabTransition($tpn(courant),$j,guard,dx) $tabTransition($tpn(courant),[expr $j+1],guard,dx)
		    set tabTransition($tpn(courant),$j,guard,dy) $tabTransition($tpn(courant),[expr $j+1],guard,dy)
		    set tabTransition($tpn(courant),$j,update,dx) $tabTransition($tpn(courant),[expr $j+1],update,dx)
		    set tabTransition($tpn(courant),$j,update,dy) $tabTransition($tpn(courant),[expr $j+1],update,dy)
		    set tabTransition($tpn(courant),$j,dmin) $tabTransition($tpn(courant),[expr $j+1],dmin)
		    set tabTransition($tpn(courant),$j,dmax) $tabTransition($tpn(courant),[expr $j+1],dmax)
		    set tabTransition($tpn(courant),$j,eftIncl) $tabTransition($tpn(courant),[expr $j+1],eftIncl)
		    set tabTransition($tpn(courant),$j,lftIncl) $tabTransition($tpn(courant),[expr $j+1],lftIncl)
		    set tabTransition($tpn(courant),$j,minparam) $tabTransition($tpn(courant),[expr $j+1],minparam)
		    set tabTransition($tpn(courant),$j,maxparam) $tabTransition($tpn(courant),[expr $j+1],maxparam)
		    set tabTransition($tpn(courant),$j,priority) $tabTransition($tpn(courant),[expr $j+1],priority)
		    set tabTransition($tpn(courant),$j,speed) $tabTransition($tpn(courant),[expr $j+1],speed)
		    set tabTransition($tpn(courant),$i,speed,dx) $tabTransition($tpn(courant),[expr $j+1],speed,dx)
		    set tabTransition($tpn(courant),$i,speed,dy) $tabTransition($tpn(courant),[expr $j+1],speed,dy)		    
		    set tabTransition($tpn(courant),$j,cost) $tabTransition($tpn(courant),[expr $j+1],cost)
		    set tabTransition($tpn(courant),$i,cost,dx) $tabTransition($tpn(courant),[expr $j+1],cost,dx)
		    set tabTransition($tpn(courant),$i,cost,dy) $tabTransition($tpn(courant),[expr $j+1],cost,dy)		    

		    
		    set tabTransition($tpn(courant),$j,Porg,1) $tabTransition($tpn(courant),[expr $j+1],Porg,1)
		    set tabTransition($tpn(courant),$j,PorgNailx,1) $tabTransition($tpn(courant),[expr $j+1],PorgNailx,1)
		    set tabTransition($tpn(courant),$j,PorgNaily,1) $tabTransition($tpn(courant),[expr $j+1],PorgNaily,1)
		    set tabTransition($tpn(courant),$j,PorgWeight,1) $tabTransition($tpn(courant),[expr $j+1],PorgWeight,1)
		    set tabTransition($tpn(courant),$j,PorgTokenColor,1) $tabTransition($tpn(courant),[expr $j+1],PorgTokenColor,1)
		    set tabTransition($tpn(courant),$j,PorgInhibitingCondition,1) $tabTransition($tpn(courant),[expr $j+1],PorgInhibitingCondition,1)
		    set tabTransition($tpn(courant),$j,PorgType,1) $tabTransition($tpn(courant),[expr $j+1],PorgType,1)
		    for {set l 2} {$tabTransition($tpn(courant),[expr $j+1],Porg,[expr $l-1]) >0} {incr l} {
			set tabTransition($tpn(courant),$j,Porg,$l) $tabTransition($tpn(courant),[expr $j+1],Porg,$l)
			set tabTransition($tpn(courant),$j,PorgNailx,$l) $tabTransition($tpn(courant),[expr $j+1],PorgNailx,$l)
			set tabTransition($tpn(courant),$j,PorgNaily,$l) $tabTransition($tpn(courant),[expr $j+1],PorgNaily,$l)
			set tabTransition($tpn(courant),$j,PorgWeight,$l) $tabTransition($tpn(courant),[expr $j+1],PorgWeight,$l)
			set tabTransition($tpn(courant),$j,PorgTokenColor,$l) $tabTransition($tpn(courant),[expr $j+1],PorgTokenColor,$l)
			set tabTransition($tpn(courant),$j,PorgInhibitingCondition,$l) $tabTransition($tpn(courant),[expr $j+1],PorgInhibitingCondition,$l)
			set tabTransition($tpn(courant),$j,PorgType,$l) $tabTransition($tpn(courant),[expr $j+1],PorgType,$l)
		    }
		    set tabTransition($tpn(courant),$j,Pdes,1) $tabTransition($tpn(courant),[expr $j+1],Pdes,1)
		    set tabTransition($tpn(courant),$j,PdesNailx,1) $tabTransition($tpn(courant),[expr $j+1],PdesNailx,1)
		    set tabTransition($tpn(courant),$j,PdesNaily,1) $tabTransition($tpn(courant),[expr $j+1],PdesNaily,1)
		    set tabTransition($tpn(courant),$j,PdesWeight,1) $tabTransition($tpn(courant),[expr $j+1],PdesWeight,1)
		    set tabTransition($tpn(courant),$j,PdesTokenColor,1) $tabTransition($tpn(courant),[expr $j+1],PdesTokenColor,1)
		    for {set l 2} {$tabTransition($tpn(courant),[expr $j+1],Pdes,[expr $l-1]) >0} {incr l}  {
			set tabTransition($tpn(courant),$j,Pdes,$l) $tabTransition($tpn(courant),[expr $j+1],Pdes,$l)
			set tabTransition($tpn(courant),$j,PdesNailx,$l) $tabTransition($tpn(courant),[expr $j+1],PdesNailx,$l)
			set tabTransition($tpn(courant),$j,PdesNaily,$l) $tabTransition($tpn(courant),[expr $j+1],PdesNaily,$l)
			set tabTransition($tpn(courant),$j,PdesWeight,$l) $tabTransition($tpn(courant),[expr $j+1],PdesWeight,$l)
			set tabTransition($tpn(courant),$j,PdesTokenColor,$l) $tabTransition($tpn(courant),[expr $j+1],PdesTokenColor,$l)
		    }
		}
	    }
	    
	}
    }
    
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin} {incr i} {
	for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0} {incr j} {
	    set tabTransition($tpn(courant),$i,Porg,$j) [expr [iPU $tabTransition($tpn(courant),$i,Porg,$j)]+1]
	}
	for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0} {incr j} {
	    set tabTransition($tpn(courant),$i,Pdes,$j) [expr [iPU $tabTransition($tpn(courant),$i,Pdes,$j)]+1]
	}
    }
    
    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
	if {$tabPlace($tpn(courant),$i,statut)==$destroy} {
	    for {set j $i} {$tabPlace($tpn(courant),$j,statut)!=$fin} {incr j} {
		set tabPlace($tpn(courant),$j,statut)  $tabPlace($tpn(courant),[expr $j+1],statut)
		if {$tabPlace($tpn(courant),[expr $j+1],statut)==$ok} {
		    set tabPlace($tpn(courant),$j,xy,x) $tabPlace($tpn(courant),[expr $j+1],xy,x)
		    set tabPlace($tpn(courant),$j,xy,y) $tabPlace($tpn(courant),[expr $j+1],xy,y)
		    set tabPlace($tpn(courant),$j,label,nom) $tabPlace($tpn(courant),[expr $j+1],label,nom)
		    set tabPlace($tpn(courant),$j,id) $tabPlace($tpn(courant),[expr $j+1],id)
		    set tabPlace($tpn(courant),$j,label,dx) $tabPlace($tpn(courant),[expr $j+1],label,dx)
		    set tabPlace($tpn(courant),$j,label,dy)  $tabPlace($tpn(courant),[expr $j+1],label,dy)
		    set tabPlace($tpn(courant),$j,processeur) $tabPlace($tpn(courant),[expr $j+1],processeur)
		    set tabPlace($tpn(courant),$j,priorite) $tabPlace($tpn(courant),[expr $j+1],priorite)
		    set tabPlace($tpn(courant),$j,jeton) $tabPlace($tpn(courant),[expr $j+1],jeton)
		}
	    }
	}
    }
}

proc dupliquerPlace {indice dx dy} {
    global tabPlace 
    global tpn tabUnDo
    global fin
    global ok
    global modif
    
    modifTPN $tpn(courant)
    for {set i 1} {$tabPlace($tpn(courant),$i,statut)==$ok} {incr i} {}
    if {$tabPlace($tpn(courant),$i,statut)==$fin} {set tabPlace($tpn(courant),[expr $i+1],statut) $fin}
    set tabPlace($tpn(courant),$i,statut) $ok
    set tabPlace($tpn(courant),$i,xy,x) [posSurGrille [expr $tabPlace($tpn(courant),$indice,xy,x)+ $dx]]
    set tabPlace($tpn(courant),$i,xy,y) [posSurGrille [expr $tabPlace($tpn(courant),$indice,xy,y)+ $dy]]
    set tabPlace($tpn(courant),$i,color) $tabPlace($tpn(courant),$indice,color)
    set tabPlace($tpn(courant),$i,dmin) $tabPlace($tpn(courant),$indice,dmin)
    set tabPlace($tpn(courant),$i,dmax) $tabPlace($tpn(courant),$indice,dmax)
    set tabPlace($tpn(courant),$i,label,nom) "$tabPlace($tpn(courant),$indice,label,nom)\_c"
    set tabPlace($tpn(courant),$i,id) [genererUniquePlaceId $i "P$indice"]
    set tabPlace($tpn(courant),$i,label,dx) $tabPlace($tpn(courant),$indice,label,dx)
    set tabPlace($tpn(courant),$i,label,dy) $tabPlace($tpn(courant),$indice,label,dy)
    set tabPlace($tpn(courant),$i,processeur) $tabPlace($tpn(courant),$indice,processeur)
    set tabPlace($tpn(courant),$i,priorite) $tabPlace($tpn(courant),$indice,priorite)
    set tabPlace($tpn(courant),$i,jeton) $tabPlace($tpn(courant),$indice,jeton)
    return $i
}

proc dupliquerTransition {indice listeP copieP copieN dx dy } {
    global tabTransition 
    global tpn tabUnDo
    global fin
    global ok
    global modif
    global tempNoeud
    
    for {set npt 1} {$tempNoeud($npt,placeNPT)>-1} {incr npt} {}
    for {set ntp 1} {$tempNoeud($ntp,placeNTP)>-1} {incr ntp} {}
    
    modifTPN $tpn(courant)
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)==$ok} {incr i} {}
    if {$tabTransition($tpn(courant),$i,statut)==$fin} {set tabTransition($tpn(courant),[expr $i+1],statut) $fin}
    set tabTransition($tpn(courant),$i,statut) $ok
    
    set tabTransition($tpn(courant),$i,color)  $tabTransition($tpn(courant),$indice,color)
    set tabTransition($tpn(courant),$i,xy,x) [posSurGrille [expr $tabTransition($tpn(courant),$indice,xy,x)+ $dx]]
    set tabTransition($tpn(courant),$i,xy,y) [posSurGrille [expr $tabTransition($tpn(courant),$indice,xy,y)+ $dy]]
    
    for {set j 1} {$tabTransition($tpn(courant),$indice,Porg,$j)!=0} {incr j} {
	set iPo [lsearch $listeP $tabTransition($tpn(courant),$indice,Porg,$j)]
	if {$iPo<0} {
	    set tabTransition($tpn(courant),$i,Porg,$j) $tabTransition($tpn(courant),$indice,Porg,$j)
	} else {
	    set tabTransition($tpn(courant),$i,Porg,$j) [lindex $copieP $iPo]
	}

	set tabTransition($tpn(courant),$i,PorgWeight,$j) $tabTransition($tpn(courant),$indice,PorgWeight,$j)
	set tabTransition($tpn(courant),$i,PorgInhibitingCondition,$j) $tabTransition($tpn(courant),$indice,PorgInhibitingCondition,$j)
	set tabTransition($tpn(courant),$i,PorgType,$j) $tabTransition($tpn(courant),$indice,PorgType,$j)
	set tabTransition($tpn(courant),$i,PorgColor,$j) $tabTransition($tpn(courant),$indice,PorgColor,$j)
	set tabTransition($tpn(courant),$i,PorgTokenColor,$j) $tabTransition($tpn(courant),$indice,PorgTokenColor,$j)
	set tabTransition($tpn(courant),$i,PorgNaily,$j) 0
	set tabTransition($tpn(courant),$i,PorgNailx,$j) 0
	
	if {$tabTransition($tpn(courant),$indice,Porg,$j)>0} {
	    set leNoeud [indiceNoeudPT $tabTransition($tpn(courant),$indice,Porg,$j) $indice $tabTransition($tpn(courant),$indice,PorgType,$j)]
	    if {$leNoeud>-1} {
		if {[lsearch $copieN $leNoeud]!=-1} {
		    set tempNoeud($npt,placeNPT) $tabTransition($tpn(courant),$i,Porg,$j)
		    set tempNoeud($npt,type) $tabTransition($tpn(courant),$i,PorgType,$j)
		    set tempNoeud($npt,transitionNPT) $i
		    incr npt
		    set tabTransition($tpn(courant),$i,PorgNaily,$j) [expr $tabTransition($tpn(courant),$indice,PorgNaily,$j) + $dy]
		    set tabTransition($tpn(courant),$i,PorgNailx,$j) [expr $tabTransition($tpn(courant),$indice,PorgNailx,$j) + $dx]
		}
	    }
	}
    }
    
    set tempNoeud($npt,placeNPT) -1
    set tempNoeud($npt,transitionNPT) -1
    set tempNoeud($npt,type) 0
    
    set tabTransition($tpn(courant),$i,Porg,$j) 0
    set tabTransition($tpn(courant),$i,PorgType,$j) 0

    set tabTransition($tpn(courant),$i,PorgWeight,$j) 1
    set tabTransition($tpn(courant),$i,PorgTokenColor,$j) -1
    set tabTransition($tpn(courant),$i,PorgInhibitingCondition,$j) ""
    set tabTransition($tpn(courant),$i,PorgColor,$j) 1
    set tabTransition($tpn(courant),$i,PorgNaily,$j) 0
    set tabTransition($tpn(courant),$i,PorgNailx,$j) 0
    
    for {set j 1} {$tabTransition($tpn(courant),$indice,Pdes,$j)!=0} {incr j} {
	set iPo [lsearch $listeP $tabTransition($tpn(courant),$indice,Pdes,$j)]
	if {$iPo<0} {
	    set tabTransition($tpn(courant),$i,Pdes,$j) $tabTransition($tpn(courant),$indice,Pdes,$j)
	} else {
	    set tabTransition($tpn(courant),$i,Pdes,$j) [lindex $copieP $iPo]
	}
	set tabTransition($tpn(courant),$i,PdesWeight,$j) $tabTransition($tpn(courant),$indice,PdesWeight,$j)
	set tabTransition($tpn(courant),$i,PdesColor,$j) $tabTransition($tpn(courant),$indice,PdesColor,$j)
	set tabTransition($tpn(courant),$i,PdesTokenColor,$j) $tabTransition($tpn(courant),$indice,PdesTokenColor,$j)
	set tabTransition($tpn(courant),$i,PdesNailx,$j) 0
	set tabTransition($tpn(courant),$i,PdesNaily,$j) 0
	if {$tabTransition($tpn(courant),$indice,Pdes,$j)>0} {
	    set leNoeud [indiceNoeudTP $indice $tabTransition($tpn(courant),$indice,Pdes,$j)]
	    if {$leNoeud>-1} {
		if {[lsearch $copieN $leNoeud]!=-1} {
		    set tempNoeud($ntp,placeNTP) $tabTransition($tpn(courant),$i,Pdes,$j)
		    set tempNoeud($ntp,transitionNTP) $i
		    incr ntp
		    set tabTransition($tpn(courant),$i,PdesNaily,$j) [expr $tabTransition($tpn(courant),$indice,PdesNaily,$j) + $dy]
		    set tabTransition($tpn(courant),$i,PdesNailx,$j) [expr $tabTransition($tpn(courant),$indice,PdesNailx,$j) + $dx]
		}
	    }
	}
    }
    set tempNoeud($ntp,placeNTP) -1
    set tempNoeud($ntp,transitionNTP) -1
    
    set tabTransition($tpn(courant),$i,Pdes,$j) 0
    set tabTransition($tpn(courant),$i,PdesWeight,$j) 1
    set tabTransition($tpn(courant),$i,PdesTokenColor,$j) -1
    set tabTransition($tpn(courant),$i,PdesColor,$j) 1
    set tabTransition($tpn(courant),$i,PdesNaily,$j) 0
    set tabTransition($tpn(courant),$i,PdesNailx,$j) 0
    
    
    set tabTransition($tpn(courant),$i,label,nom) "$tabTransition($tpn(courant),$indice,label,nom)\_c"
    set tabTransition($tpn(courant),$i,id) [genererUniqueTransId $i "T$indice"]
    set tabTransition($tpn(courant),$i,label,dx) $tabTransition($tpn(courant),$indice,label,dx)
    set tabTransition($tpn(courant),$i,label,dy) $tabTransition($tpn(courant),$indice,label,dy)
    set tabTransition($tpn(courant),$i,guard,dx) $tabTransition($tpn(courant),$indice,guard,dx)
    set tabTransition($tpn(courant),$i,guard,dy) $tabTransition($tpn(courant),$indice,guard,dy)
    set tabTransition($tpn(courant),$i,update,dx) $tabTransition($tpn(courant),$indice,update,dx)
    set tabTransition($tpn(courant),$i,update,dy) $tabTransition($tpn(courant),$indice,update,dy)
    
    set tabTransition($tpn(courant),$i,priority) $tabTransition($tpn(courant),$indice,priority)

    set tabTransition($tpn(courant),$i,speed) $tabTransition($tpn(courant),$indice,speed)
    set tabTransition($tpn(courant),$i,speed,dx) $tabTransition($tpn(courant),$indice,speed,dx)
    set tabTransition($tpn(courant),$i,speed,dy) $tabTransition($tpn(courant),$indice,speed,dy)
    set tabTransition($tpn(courant),$i,cost) $tabTransition($tpn(courant),$indice,cost)
    set tabTransition($tpn(courant),$i,cost,dx) $tabTransition($tpn(courant),$indice,cost,dx)
    set tabTransition($tpn(courant),$i,cost,dy) $tabTransition($tpn(courant),$indice,cost,dy)

    set tabTransition($tpn(courant),$i,dmin) $tabTransition($tpn(courant),$indice,dmin)
    set tabTransition($tpn(courant),$i,dmax) $tabTransition($tpn(courant),$indice,dmax)
    set tabTransition($tpn(courant),$i,eftIncl) $tabTransition($tpn(courant),$indice,eftIncl)
    set tabTransition($tpn(courant),$i,lftIncl) $tabTransition($tpn(courant),$indice,lftIncl)
    set tabTransition($tpn(courant),$i,minparam) $tabTransition($tpn(courant),$indice,minparam)
    set tabTransition($tpn(courant),$i,maxparam) $tabTransition($tpn(courant),$indice,maxparam)
    set tabTransition($tpn(courant),$i,obs) $tabTransition($tpn(courant),$indice,obs)
    set tabTransition($tpn(courant),$i,unctrl) $tabTransition($tpn(courant),$indice,unctrl)
    set tabTransition($tpn(courant),$i,update) $tabTransition($tpn(courant),$indice,update) 
    set tabTransition($tpn(courant),$i,guard) $tabTransition($tpn(courant),$indice,guard) 


    return $i
}

#********************** coller une place d'un TPN vers un autre  *******************

proc collerPlace {tpnSource indicePlace tpnDestination} {
    global tabPlace
    global tpn tabUnDo
    global fin ok destroy
    global insertTPN
    global infini
    global nbPlaceMax

    for {set i 1} {$tabPlace($tpnDestination,$i,statut)==$ok} {incr i} {}
    if {$tabPlace($tpnDestination,$i,statut)==$fin} {set tabPlace($tpnDestination,[expr $i+1],statut) $fin}

    set tabPlace($tpnDestination,$i,statut)   $tabPlace($tpnSource,$indicePlace,statut) 
    set tabPlace($tpnDestination,$i,color) $tabPlace($tpnSource,$indicePlace,color)
    set tabPlace($tpnDestination,$i,label,nom) $tabPlace($tpnSource,$indicePlace,label,nom)
    set tabPlace($tpnDestination,$i,id) [genererUniquePlaceId $i $tabPlace($tpnSource,$indicePlace,id)]
    set tabPlace($tpnDestination,$i,label,dx) $tabPlace($tpnSource,$indicePlace,label,dx)
    set tabPlace($tpnDestination,$i,label,dy)  $tabPlace($tpnSource,$indicePlace,label,dy)
    set tabPlace($tpnDestination,$i,processeur) $tabPlace($tpnSource,$indicePlace,processeur)
    set tabPlace($tpnDestination,$i,priorite) $tabPlace($tpnSource,$indicePlace,priorite)
    set tabPlace($tpnDestination,$i,jeton) $tabPlace($tpnSource,$indicePlace,jeton)
    set tabPlace($tpnDestination,$i,xy,x) $tabPlace($tpnSource,$indicePlace,xy,x)
    set tabPlace($tpnDestination,$i,xy,y) $tabPlace($tpnSource,$indicePlace,xy,y)
    set tabPlace($tpnDestination,$i,dmin) $tabPlace($tpnSource,$indicePlace,dmin)
    set tabPlace($tpnDestination,$i,dmax) $tabPlace($tpnSource,$indicePlace,dmax)

return $i
}

#********************** coller une transition d'un TPN vers un autre  *******************

proc collerTransition {tpnSource indiceTransition listePlacesSource tpnDestination listePlacesDestination} { 
    global tabTransition
    global tpn tabUnDo
    global fin ok destroy
    global insertTPN
    global infini

    for {set i 1} {$tabTransition($tpnDestination,$i,statut)==$ok} {incr i} {}
    if {$tabTransition($tpnDestination,$i,statut)==$fin} {set tabTransition($tpnDestination,[expr $i+1],statut) $fin}

    set tabTransition($tpnDestination,$i,statut) $tabTransition($tpnSource,$indiceTransition,statut) 
    set tabTransition($tpnDestination,$i,color) $tabTransition($tpnSource,$indiceTransition,color) 
    set tabTransition($tpnDestination,$i,dmin) $tabTransition($tpnSource,$indiceTransition,dmin) 
    set tabTransition($tpnDestination,$i,dmax) $tabTransition($tpnSource,$indiceTransition,dmax) 
    set tabTransition($tpnDestination,$i,eftIncl) $tabTransition($tpnSource,$indiceTransition,eftIncl) 
    set tabTransition($tpnDestination,$i,lftIncl) $tabTransition($tpnSource,$indiceTransition,lftIncl) 
    set tabTransition($tpnDestination,$i,priority) $tabTransition($tpnSource,$indiceTransition,priority) 
    set tabTransition($tpnDestination,$i,speed) $tabTransition($tpnSource,$indiceTransition,speed) 
    set tabTransition($tpnDestination,$i,cost) $tabTransition($tpnSource,$indiceTransition,cost)
    set tabTransition($tpnDestination,$i,minparam) $tabTransition($tpnSource,$indiceTransition,minparam)
    set tabTransition($tpnDestination,$i,maxparam) $tabTransition($tpnSource,$indiceTransition,maxparam) 
    set tabTransition($tpnDestination,$i,label,nom) $tabTransition($tpnSource,$indiceTransition,label,nom) 
    set tabTransition($tpnDestination,$i,id) [genererUniqueTransId $i $tabTransition($tpnSource,$indiceTransition,id)]

    set k 1
    for {set j 1} {$tabTransition($tpnSource,$indiceTransition,Porg,$j)!=0} {incr j} {
	set iPo [lsearch $listePlacesSource $tabTransition($tpnSource,$indiceTransition,Porg,$j)]
	if {$iPo>=0} {
	    set tabTransition($tpnDestination,$i,Porg,$k) [lindex $listePlacesDestination $iPo]
	    set tabTransition($tpnDestination,$i,PorgInhibitingCondition,$k) $tabTransition($tpnSource,$indiceTransition,PorgInhibitingCondition,$k)
	    set tabTransition($tpnDestination,$i,PorgWeight,$k) $tabTransition($tpnSource,$indiceTransition,PorgWeight,$k)
	    set tabTransition($tpnDestination,$i,PorgNailx,$k) $tabTransition($tpnSource,$indiceTransition,PorgNailx,$k)
	    set tabTransition($tpnDestination,$i,PorgNaily,$k) $tabTransition($tpnSource,$indiceTransition,PorgNaily,$k)
	    set tabTransition($tpnDestination,$i,PorgColor,$k) $tabTransition($tpnSource,$indiceTransition,PorgColor,$k)
	    set tabTransition($tpnDestination,$i,PorgTokenColor,$k) $tabTransition($tpnSource,$indiceTransition,PorgTokenColor,$k)
	    set tabTransition($tpnDestination,$i,PorgType,$k) $tabTransition($tpnSource,$indiceTransition,PorgType,$k)
	    set tabTransition($tpnDestination,$i,PorgTokenColor,$k) $tabTransition($tpnSource,$indiceTransition,PorgTokenColor,$k)
	    set k [expr $k+1]
	} 
    }
    set tabTransition($tpnDestination,$i,Porg,$k) 0
    set tabTransition($tpnDestination,$i,PorgWeight,$k) 1
    set tabTransition($tpnDestination,$i,PorgInhibitingCondition,$k) ""
    set tabTransition($tpnDestination,$i,PorgColor,$k) 1
    set tabTransition($tpnDestination,$i,PorgNaily,$k) 0
    set tabTransition($tpnDestination,$i,PorgNailx,$k) 0
    set tabTransition($tpnDestination,$i,PorgType,$k) 1 
    set tabTransition($tpnDestination,$i,PorgTokenColor,$k) -1


    set k 1
     for {set j 1} {$tabTransition($tpnSource,$indiceTransition,Pdes,$j)!=0} {incr j} {
	set iPo [lsearch $listePlacesSource $tabTransition($tpnSource,$indiceTransition,Pdes,$j)]
	if {$iPo>=0} {
	    set tabTransition($tpnDestination,$i,Pdes,$k) [lindex $listePlacesDestination $iPo]
	    set tabTransition($tpnDestination,$i,PdesWeight,$k) $tabTransition($tpnSource,$indiceTransition,PdesWeight,$k)
	    set tabTransition($tpnDestination,$i,PdesNailx,$k) $tabTransition($tpnSource,$indiceTransition,PdesNailx,$k)
	    set tabTransition($tpnDestination,$i,PdesNaily,$k) $tabTransition($tpnSource,$indiceTransition,PdesNaily,$k)
	    set tabTransition($tpnDestination,$i,PdesColor,$k) $tabTransition($tpnSource,$indiceTransition,PdesColor,$k)
	    set tabTransition($tpnDestination,$i,PdesTokenColor,$k) $tabTransition($tpnSource,$indiceTransition,PdesTokenColor,$k)
	    set k [expr $k+1]
	} 
    }
    set tabTransition($tpnDestination,$i,Pdes,$k) 0
    set tabTransition($tpnDestination,$i,Pdes,$k) 0
    set tabTransition($tpnDestination,$i,PdesWeight,$k) 1
    set tabTransition($tpnDestination,$i,PdesColor,$k) 1
    set tabTransition($tpnDestination,$i,PdesNaily,$k) 0
    set tabTransition($tpnDestination,$i,PdesNailx,$k) 0
    set tabTransition($tpnDestination,$i,PdesTokenColor,$k) -1

    set tabTransition($tpnDestination,$i,label,dx) $tabTransition($tpnSource,$indiceTransition,label,dx)
    set tabTransition($tpnDestination,$i,label,dy) $tabTransition($tpnSource,$indiceTransition,label,dy)
    set tabTransition($tpnDestination,$i,guard,dx) $tabTransition($tpnSource,$indiceTransition,guard,dx)
    set tabTransition($tpnDestination,$i,guard,dy) $tabTransition($tpnSource,$indiceTransition,guard,dy)
    set tabTransition($tpnDestination,$i,update,dx) $tabTransition($tpnSource,$indiceTransition,update,dx)
    set tabTransition($tpnDestination,$i,update,dy) $tabTransition($tpnSource,$indiceTransition,update,dy)
    set tabTransition($tpnDestination,$i,speed,dx) $tabTransition($tpnSource,$indiceTransition,speed,dx)
    set tabTransition($tpnDestination,$i,speed,dy) $tabTransition($tpnSource,$indiceTransition,speed,dy)
    set tabTransition($tpnDestination,$i,cost,dx) $tabTransition($tpnSource,$indiceTransition,cost,dx)
    set tabTransition($tpnDestination,$i,cost,dy) $tabTransition($tpnSource,$indiceTransition,cost,dy)
    set tabTransition($tpnDestination,$i,xy,x) $tabTransition($tpnSource,$indiceTransition,xy,x)
    set tabTransition($tpnDestination,$i,xy,y) $tabTransition($tpnSource,$indiceTransition,xy,y)
    set tabTransition($tpnDestination,$i,obs) $tabTransition($tpnSource,$indiceTransition,obs)
    set tabTransition($tpnDestination,$i,unctrl) $tabTransition($tpnSource,$indiceTransition,unctrl)
    set tabTransition($tpnDestination,$i,guard) $tabTransition($tpnSource,$indiceTransition,guard)
    set tabTransition($tpnDestination,$i,update) $tabTransition($tpnSource,$indiceTransition,update)

return $i
}


proc doubleClickWeight {c k slave} {
    global plot
    global tabTransition tabPlace 
    global tpn tabUnDo
    global modif
    global francais
    global maxX maxY zoom
    global tabFlechePT tabFlecheTP tabNoeud
    global fin
    global nouveauWeight 
    global simulatorOn semaphore
    global couleurCourante tabColor resultatCouleur

majcanvas $c $slave

 set semaphore(Release) 0
 doubleClickFPT $c $k $slave

}

proc doubleClickFPT {c k slave} {
    global plot
    global tabTransition tabPlace 
    global tpn tabUnDo
    global modif
    global francais
    global maxX maxY zoom
    global tabFlechePT tabFlecheTP tabNoeud
    global fin
    global nouveauWeight nouveauTokenColor nbTokenColor
    global simulatorOn semaphore
    global couleurCourante tabColor resultatCouleur 

majcanvas $c $slave

 set semaphore(Release) 0
    if {$simulatorOn!=1} {
	
	set T $tabFlechePT($k,transition)
	set P $tabFlechePT($k,place)
	set type $tabFlechePT($k,type)
	for {set indice 1} {($tabTransition($tpn(courant),$T,Porg,$indice)!=$P)||($tabTransition($tpn(courant),$T,PorgType,$indice)!=$type)}  {incr indice} {}
	set nouveauWeight $tabTransition($tpn(courant),$T,PorgWeight,$indice)
	
	set f .fenetreArc
	catch {destroy $f}
	toplevel $f
	
	set deltaX [lindex [$c xview] 0]
	set x [expr int(($tabTransition($tpn(courant),$T,xy,x)-$maxX*$deltaX)*$zoom +[winfo rootx $c]) - 20]
	set deltaY [lindex [$c yview] 0]
	set y [expr int(($tabTransition($tpn(courant),$T,xy,y)-$maxY*$deltaY)*$zoom +[winfo rooty $c]) - 20]

	set sw [winfo screenwidth $f]
      set sh [winfo screenheight $f]

      set x [expr {max(0, min($x, $sw-100))}]   ;# 100 = largeur fenÃªtre
      set y [expr {max(0, min($y, $sh-50))}]    ;# 50 = hauteur fenÃªtre

	wm geometry $f +$x+$y
    wm title $f "Arc parameters : "
	
	label $f.nom -bd 2
	pack $f.nom -side top -fill x -pady 2m
	
	$f.nom config -text "Type : [nomTypeArc $type]  \n Arc : Place($P) -> transition($T) \n $tabPlace($tpn(courant),$P,id) -> $tabTransition($tpn(courant),$T,id) \n " -justify center -font menufont
	
	# Si c'est un arc normal ou read ou inhibitor logique
	# cad si ce n'est pas un flush
	if {($type!=1)} {
	  frame $f.weight -bd 2 
	  pack $f.weight -side top -fill x -pady 2m
	  entry $f.weight.saisie -justify left -textvariable nouveauWeight -font menufont -relief sunken -width 7 -bg white
	  label $f.weight.label
	  pack $f.weight.label -side left
	  pack $f.weight.saisie -side left
	  $f.weight.label config -text "weight:  " -font menufont

	}


	if {$nbTokenColor($tpn(courant))>1} {
	    set nouveauTokenColor $tabTransition($tpn(courant),$T,PorgTokenColor,$indice)
	    frame $f.tokencolor -bd 2 
	    pack $f.tokencolor -side top -fill x -pady 2m
	    label $f.tokencolor.label
	    pack $f.tokencolor.label -side left

	    $f.tokencolor.label config -text "Token color:  " -font menufont

	    
	    set laTokenColor -1
	    frame $f.tokencolor.couleurAny -bd 2 
	    pack $f.tokencolor.couleurAny -side top -fill x -anchor w
	    
	    radiobutton $f.tokencolor.couleurAny.bouton -text "Any" -variable nouveauTokenColor -font menufont -value $laTokenColor -selectcolor red 
	    pack $f.tokencolor.couleurAny.bouton -side left 
	    paletteCouleurTokenbColorGLOP $f.tokencolor.couleurAny $laTokenColor

	    for {set laTokenColor 0} {$laTokenColor<$nbTokenColor($tpn(courant))} {incr laTokenColor} {
		frame $f.tokencolor.couleur$laTokenColor -bd 2 
		pack $f.tokencolor.couleur$laTokenColor -side top 

		radiobutton $f.tokencolor.couleur$laTokenColor.bouton -text "color $laTokenColor" -font menufont -variable nouveauTokenColor -value $laTokenColor -selectcolor red 
		pack $f.tokencolor.couleur$laTokenColor.bouton -side left 
		paletteCouleurTokenbColorGLOP $f.tokencolor.couleur$laTokenColor $laTokenColor
	    }

	}

	# Si c'est un timed  inhibitor 

	if {($type==4)} {

	    frame $f.condition -relief ridge -bd 2
	    pack $f.condition -side top
	    label $f.condition.label
	    pack  $f.condition.label -side left
	    $f.condition.label config -text "Inhibiting condition (0 or 1):  " -font menufont

	    text $f.condition.text -yscrollcommand "$f.condition.scroll set" -setgrid true \
		-width 30 -height 3 -wrap word -bg white -font menufont
	    scrollbar $f.condition.scroll -command "$f.condition.text yview" 

	    pack $f.condition.scroll -side right -fill y 
	    pack $f.condition.text -expand yes -fill both 

	    $f.condition.text insert end $tabTransition($tpn(courant),$T,PorgInhibitingCondition,$indice)

	}
#---------------------------------------------- La couleur du dessin
	set resultatCouleur(Arc) $tabTransition($tpn(courant),$T,PorgColor,$indice)
	if {$nbTokenColor($tpn(courant))<=1} {
	    frame $f.color -bd 2
	    pack $f.color -side top
	    label $f.color.label
	    pack $f.color.label -side left
	    $f.color.label config -text "color:  " -font menufont
	    
	    selectionCouleur $f.color Arc
	}
#---------------------------------------------- 
#	bind $f <Return> "validerArcPT $c $f $T $indice $type"
	bind $f <Escape> "destroy $f"
	frame $f.buttons
	pack $f.buttons -side bottom -fill x -pady 2m
	if {($type==4)} {
	    button $f.buttons.annuler -text Cancel -font menufont -command  "destroy $f"
	    button $f.buttons.accepter -text "  Ok  " -font menufont \
		-command "validerArcPT $c $f $T $indice $type"
	} else {
	    bind $f <Return> "validerArcPT $c $f $T $indice $type"
	    button $f.buttons.annuler -text Cancel -font menufont -command  "destroy $f"
	    button $f.buttons.accepter -default active -text "  Ok  " -font menufont \
		-command "validerArcPT $c $f $T $indice $type"
	}
	pack $f.buttons.accepter $f.buttons.annuler  -side left -expand 1
    } 
    
    
    #++++++ procedures internes à doubleClickArc
    
    proc validerArcPT {c f numT indice type} {
	global nouveauWeight nouveauTokenColor nbTokenColor
	global tabTransition 
	global tpn tabUnDo
	global modif
	global resultatCouleur couleurCourante 
	
	modifTPN $tpn(courant)

	if {$nbTokenColor($tpn(courant))<=1} {
	    set tabTransition($tpn(courant),$numT,PorgColor,$indice) $resultatCouleur(Arc)
	    set couleurCourante(Arc) $resultatCouleur(Arc)
	} else {
	    if {$nouveauTokenColor==-1} {
		set tabTransition($tpn(courant),$numT,PorgColor,$indice) -1
	    } else {
		set tabTransition($tpn(courant),$numT,PorgColor,$indice) [expr $nouveauTokenColor % 14]
	    }
	    set couleurCourante(Arc) 5
	}

       if {[catch  {set res [format %d $nouveauWeight]}]} {
	   set res $nouveauWeight
           tk_messageBox -message "Make sure that $nouveauWeight is an integer " -icon warning
        }

	if {$res > 0} {
	    set tabTransition($tpn(courant),$numT,PorgWeight,$indice) $res
	}


	
	if {$nbTokenColor($tpn(courant))>0} {
	    set tabTransition($tpn(courant),$numT,PorgTokenColor,$indice) $nouveauTokenColor
	}

	if {($type==4)} {
	    set nouvInhibitingCondition [$f.condition.text get 1.0 {end -1c}]
	    set erreurInhibiting [verifSyntaxeGarde $nouvInhibitingCondition]
	    if {$erreurInhibiting!= ""} {
		set button [tk_messageBox -icon error -message  "Syntax Error in InhibitingCondition $nouvInhibitingCondition : \n $erreurInhibiting"]
	    } else {
		set tabTransition($tpn(courant),$numT,PorgInhibitingCondition,$indice) $nouvInhibitingCondition
	    }
	}
    destroy $f
	redessinerRdP $c
    }
}


proc doubleClickFTP {c k slave} {
    global plot
    global tabTransition tabPlace 
    global tpn tabUnDo
    global modif
    global francais
    global maxX maxY zoom
    global tabFlechePT tabFlecheTP tabNoeud
    global fin
    global nouveauWeight nouveauTokenColor nbTokenColor
    global simulatorOn semaphore
    global couleurCourante tabColor resultatCouleur 
    
majcanvas $c $slave

 set semaphore(Release) 0
    if {$simulatorOn!=1} {
	
	set T $tabFlecheTP($k,transition)
	set P $tabFlecheTP($k,place)
	for {set indice 1} { $tabTransition($tpn(courant),$T,Pdes,$indice) != $P}  {incr indice} {}
	set nouveauWeight $tabTransition($tpn(courant),$T,PdesWeight,$indice)
	
	set f .fenetreArc
	catch {destroy $f}
	toplevel $f
	
	set deltaX [lindex [$c xview] 0]
	set x [expr int(($tabTransition($tpn(courant),$T,xy,x)-$maxX*$deltaX)*$zoom +[winfo rootx $c]) -20]
	set deltaY [lindex [$c yview] 0]
	set y [expr int(($tabTransition($tpn(courant),$T,xy,y)-$maxY*$deltaY)*$zoom +[winfo rooty $c]) - 20]
      set sw [winfo screenwidth $f]
      set sh [winfo screenheight $f]

      set x [expr {max(0, min($x, $sw-100))}]   ;# 100 = largeur fenÃªtre
      set y [expr {max(0, min($y, $sh-50))}]    ;# 50 = hauteur fenÃªtre

	wm geometry $f +$x+$y
    wm title $f "Arc parameters : "
	
	label $f.nom -bd 2
	pack $f.nom -side top -fill x -pady 2m
	
	$f.nom config -text "Type : TransitionPlace \n Arc : transition($T) -> Place($P) \n $tabTransition($tpn(courant),$T,id) -> $tabPlace($tpn(courant),$P,id) \n" -font menufont
	
	frame $f.weight -bd 2
	pack $f.weight -side top -fill x -pady 2m
	entry $f.weight.saisie -justify left -textvariable nouveauWeight -font menufont -relief sunken -width 7 -bg white
	label $f.weight.label
	pack $f.weight.label -side left
	pack $f.weight.saisie -side left
	$f.weight.label config -text "weight:  " -font menufont




	if {$nbTokenColor($tpn(courant))>1} {
	    set nouveauTokenColor $tabTransition($tpn(courant),$T,PdesTokenColor,$indice)
	    frame $f.tokencolor -bd 2 
	    pack $f.tokencolor -side top -fill x -pady 2m
	    label $f.tokencolor.label
	    pack $f.tokencolor.label -side left

	    $f.tokencolor.label config -text "Token color:  " -font menufont

	    
	    set laTokenColor -1
	    frame $f.tokencolor.couleurAny -bd 2 
	    pack $f.tokencolor.couleurAny -side top -fill x -anchor w
	    
	    radiobutton $f.tokencolor.couleurAny.bouton -text "Any" -variable nouveauTokenColor -font menufont -value $laTokenColor -selectcolor red 
	    pack $f.tokencolor.couleurAny.bouton -side left 
	    paletteCouleurTokenbColorGLOP $f.tokencolor.couleurAny $laTokenColor

	    for {set laTokenColor 0} {$laTokenColor<$nbTokenColor($tpn(courant))} {incr laTokenColor} {
		frame $f.tokencolor.couleur$laTokenColor -bd 2 
		pack $f.tokencolor.couleur$laTokenColor -side top 

		radiobutton $f.tokencolor.couleur$laTokenColor.bouton -text "color $laTokenColor" -font menufont -variable nouveauTokenColor -value $laTokenColor -selectcolor red 
		pack $f.tokencolor.couleur$laTokenColor.bouton -side left 
		paletteCouleurTokenbColorGLOP $f.tokencolor.couleur$laTokenColor $laTokenColor
	    }
       

	}


#---------------------------------------------- La couleur du dessin
	set resultatCouleur(Arc) $tabTransition($tpn(courant),$T,PdesColor,$indice)
	if {$nbTokenColor($tpn(courant))<=1} {
	    frame $f.color -bd 2
	    pack $f.color -side top
	    label $f.color.label
	    pack $f.color.label -side left
	    $f.color.label config -text "color:  " -font menufont
	    
	    selectionCouleur $f.color Arc
	}
#---------------------------------------------- 

	
	bind $f <Return> "validerArcTP $c $f $T $indice"
	bind $f <Escape> "destroy $f"
	frame $f.buttons
	pack $f.buttons -side bottom -fill x -pady 2m
	if {$francais==1} {
	    button $f.buttons.annuler -text Annuler -command  "destroy $f"
	    button $f.buttons.accepter -default active -text "Accepter" -font menufont \
		-command "validerArcTP $c $f $T $indice"
	} else {
	    button $f.buttons.annuler -text Cancel -font menufont -command  "destroy $f"
	    button $f.buttons.accepter -default active -text "  Ok  " -font menufont \
		-command "validerArcTP $c $f $T $indice"
	}
	pack $f.buttons.accepter $f.buttons.annuler  -side left -expand 1
    } 
    #++++++ procedures internes à doubleClickArc
    
    proc validerArcTP {c f numT indice} {
	global nouveauWeight nouveauTokenColor nbTokenColor
	global tabTransition 
	global tpn tabUnDo
	global modif
	global resultatCouleur couleurCourante 
	
	modifTPN $tpn(courant)

	if {$nbTokenColor($tpn(courant))<=1} {
	    set tabTransition($tpn(courant),$numT,PdesColor,$indice) $resultatCouleur(Arc)
	    set couleurCourante(Arc) $resultatCouleur(Arc)
	} else {
	    if {$nouveauTokenColor==-1} {
		set tabTransition($tpn(courant),$numT,PdesColor,$indice) -1
	    } else {
		set tabTransition($tpn(courant),$numT,PdesColor,$indice) [expr $nouveauTokenColor % 14]
	    }
	    set couleurCourante(Arc) 5
	}
	
	if {[catch  {set res [format %d $nouveauWeight]}]} {
	   set res $nouveauWeight
           tk_messageBox -message "Make sure that $nouveauWeight is an integer " -icon warning 
        }

	if {$res > 0} {
	    set tabTransition($tpn(courant),$numT,PdesWeight,$indice) $res
	}

	if {$nbTokenColor($tpn(courant))>0} {
	    set tabTransition($tpn(courant),$numT,PdesTokenColor,$indice) $nouveauTokenColor
	}
	destroy $f
	redessinerRdP $c
    }
}

# ++++++++++++++++++++++++++++++++ LES COULEURS ++++++++++++++++++++++++++++

proc selectionCouleur {f objet} {
global resultatCouleur tabColor

    frame $f.choix -bd 2
    pack $f.choix -side left   
    frame $f.choix.un -bd 2
    pack $f.choix.un -side left   
	for {set i 0} {$i <= 2}   {incr i} {
       radiobutton $f.choix.un.c$i -text "color $i : $tabColor($objet,$i)" -variable resultatCouleur($objet) \
		    -relief flat  -value $i  -width 16 -anchor w -bg $tabColor($objet,$i)
	   pack $f.choix.un.c$i  -side top -pady 2 -anchor w 
	}
    frame $f.choix.deux -bd 2
    pack $f.choix.deux -side left   
	for {set i 3} {$i <= 5}   {incr i} {
       radiobutton $f.choix.deux.c$i -text "color $i : $tabColor($objet,$i)"  -variable resultatCouleur($objet) \
		    -relief flat  -value $i  -width 16 -anchor w -bg $tabColor($objet,$i)
	   pack $f.choix.deux.c$i  -side top -pady 2 -anchor w 
	}
 
}

proc paletteCouleurTokenbColorGLOP {f numColor} {
global  tabColor

    button $f.choix$numColor -fg $tabColor(Arc,$numColor) -text Palette -command "changeArcTokenColor $f.choix$numColor $numColor"  
    pack $f.choix$numColor -side right

 }

proc paletteCouleur {f objet} {
global  tabColorLocal

#set tabColor(Place,5) red
	label $f.label -text "$objet:  " -font menufont
	pack $f.label -side left

    frame $f.choix -bd 2
    pack $f.choix -side left   
	for {set i 0} {$i <= 5}   {incr i} {
 	   frame $f.choix.b$i -bd 2
       pack $f.choix.b$i -side top
	   label $f.choix.b$i.couleur -text color$i -width 12 -bg $tabColorLocal($objet,$i)
	   button $f.choix.b$i.palette -bg yellow -text Palette -command "changeColor $f $objet $i" 
       pack $f.choix.b$i.couleur -side left 
       pack $f.choix.b$i.palette -side left 
	}
 
 }
 
proc changeArcTokenColor {f numColor} {
global tabColor resultat

 set resultat [tk_chooseColor -initialcolor gray -title "Choose color"]
 if {[string compare $resultat ""]} {
     set tabColor(Arc,$numColor) $resultat
     $f configure -fg $resultat
 } 
}


proc changeColor {f objet i} {
global tabColorLocal resultat

 set colorPrec $tabColorLocal($objet,$i) 
 set resultat [tk_chooseColor -initialcolor gray -title "Choose color"]
 if {[string compare $resultat ""]} {
  set tabColorLocal($objet,$i) $resultat
  if {[string compare $colorPrec $tabColorLocal($objet,$i)]} { 
   destroy $f.label
   destroy $f.choix
#   save_preferences
   paletteCouleur $f $objet
  } 
 } 
}

proc defaultPalette {f} {
global tabColorLocal defaultTabColor

  for {set i 0} {$i <= 5}   {incr i} {
    set tabColorLocal(Place,$i) $defaultTabColor(Place,$i)
    set tabColorLocal(Transition,$i) $defaultTabColor(Transition,$i)
    set tabColorLocal(Arc,$i) $defaultTabColor(Arc,$i)
  }

    destroy $f.colorPlace.label
    destroy $f.colorPlace.choix
    paletteCouleur $f.colorPlace Place

    destroy $f.colorTransition.label
    destroy $f.colorTransition.choix
    paletteCouleur $f.colorTransition Transition
    
    destroy $f.colorArc.label
    destroy $f.colorArc.choix
    paletteCouleur $f.colorArc Arc

}

proc saveAsDefaultPalette {} {
global tabColorLocal defaultTabColor

  for {set i 0} {$i <= 5}   {incr i} {
    set defaultTabColor(Place,$i) $tabColorLocal(Place,$i)
    set defaultTabColor(Transition,$i) $tabColorLocal(Transition,$i)
    set defaultTabColor(Arc,$i) $tabColorLocal(Arc,$i)
  }
  
  	save_preferences
}


proc changerCouleurSelection {c} {
    global tabColor  resultatCouleur couleurCourante

    set resultatCouleur(Place) $couleurCourante(Place)  
    set resultatCouleur(Transition) $couleurCourante(Transition)  
    set resultatCouleur(Arc) $couleurCourante(Arc)


    set top .fenetreSelectionCouleur
    catch {destroy $top}
    toplevel $top
    wm title $top "Change colors of the selection bloc:  "

    $top config 

#	label $top.label -text "Change colors of the selection bloc:  "
#	pack $top.label -side top
    frame $top.palette -bd 2 -relief sunken
    pack $top.palette -side top
    frame $top.palette.place -bd 2
    pack $top.palette.place -side left
    frame $top.palette.transition -bd 2
    pack $top.palette.transition -side left
    frame $top.palette.arc -bd 2
    pack $top.palette.arc -side left
    
    label $top.palette.place.label -bd 2 -text "Place" -font menufont
    pack $top.palette.place.label -side left
    selectionCouleur $top.palette.place Place

    label $top.palette.transition.label -bd 2 -text "Transition" -font menufont
    pack $top.palette.transition.label -side left
    selectionCouleur $top.palette.transition Transition
 
     label $top.palette.arc.label -bd 2 -text "Arc" -font menufont
    pack $top.palette.arc.label -side left
    selectionCouleur $top.palette.arc Arc

    bind $top <Return> "validerCouleurSelection $top $c"
    frame $top.buttons 
    pack $top.buttons -side bottom -fill x -pady 2m
    button $top.buttons.annuler -text [mc "Cancel"] -font menufont -command  "annulerCouleurSelection $top" 
    button $top.buttons.accepter -default active  -text [mc "Apply"]  -font menufont \
	-command "validerCouleurSelection $top $c"
    pack $top.buttons.accepter $top.buttons.annuler  -side left -expand 1

    # +++ procedures interne à la procedure map

  proc validerCouleurSelection {f c} {
   global couleurCourante resultatCouleur

   set couleurCourante(Place) $resultatCouleur(Place)
   set couleurCourante(Transition) $resultatCouleur(Transition)
   set couleurCourante(Arc) $resultatCouleur(Arc)
   changerCouleurDeLaSelection
   # cette procedure est dans manitag
   
   destroy $f
   redessinerRdP $c

  }

  proc annulerCouleurSelection {f} {
 
	destroy $f
  }


}

# procedure pour le scheduling : une Transition ne doit pas avoir deux place amont associées à un  processeur

proc incompatibleTransForScheduling {letpn laPlace} {
    global tabPlace tabTransition ok fin

    set reponse 0
    for {set i 1} {$tabTransition($letpn,$i,statut)!=$fin} {incr i} {
       if {$tabTransition($letpn,$i,statut)==$ok} {
	 for {set j 1} {$tabTransition($letpn,$i,Porg,$j)>0} {incr j} {
	     if {$tabTransition($letpn,$i,Porg,$j)==$laPlace} {
		 if {[schedulingTransition $letpn $i]>0} {
		     set reponse $i
		 }
	     }
	 }
       }
    }

return $reponse
}

proc schedulingTransition {letpn laTransition} {   
    global tabPlace tabTransition 
     set scheduledT 0
     for {set i 1} {$tabTransition($letpn,$laTransition,Porg,$i) >0}   {incr i} {
	if {$tabPlace($letpn,$tabTransition($letpn,$laTransition,Porg,$i),processeur)>0} { set scheduledT 1}
    }
 return $scheduledT
 }


proc alphanumerique {chaine} {   

    set alphanum " abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    set resul ""
    for {set i 0} {$i < [string length $chaine]} {incr i} {
	set car [string index $chaine $i]
	if { [string first $car $alphanum]>=0} {
	    set resul $resul$car
	}
    }
 return $resul
 }

proc uneLettreaudebut {chaine} {   

#Verifier si premier caractere n'est pas un chiffre

    set chiffre "0123456789_"
    if {[string first  [string index $chaine 0] $chiffre]>=0} {
	    set resul "a$chaine"
    } else {
	set resul $chaine
    }
    return $resul
 }

proc genererUniquePlaceId {laPlace identifier} {
    global tpn tabPlace tabTransition 
    global fin ok

    set numCopie 1
    set copieIdentifier [sansEspace $identifier]
    if {($copieIdentifier=="A")||($copieIdentifier=="a")} {
      set copieIdentifier "P$copieIdentifier"
    }
    while {[uniquePlaceId $laPlace $copieIdentifier]==0} {
	set copieIdentifier "$identifier\_$numCopie"
	set numCopie [expr $numCopie+1]
    }
    return $copieIdentifier
}

proc uniquePlaceId {laPlace identifier} {   
    global tpn tabPlace tabTransition 
    global fin ok


    set result 1
    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
	if {($tabPlace($tpn(courant),$i,statut)==$ok)&&($i!=$laPlace)} {
	    if {$tabPlace($tpn(courant),$i,id)==$identifier} {
		set result 0
	    }
	}
    }
    return $result
 }

proc genererUniqueTransId {laTransition identifier} {
    global tpn tabPlace tabTransition 
    global fin ok


    set numCopie 1
    set copieIdentifier [sansEspace $identifier]
    if {($copieIdentifier=="A")||($copieIdentifier=="a")} {
      set copieIdentifier "T$copieIdentifier"
    }
    while {[uniqueTransId $laTransition $copieIdentifier]==0} {
	set copieIdentifier "$identifier\_$numCopie"
	set numCopie [expr $numCopie+1]
    }
    return $copieIdentifier
}

proc uniqueTransId {laTransition identifier} {   
    global tpn tabPlace tabTransition 
    global fin ok


    set result 1
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin} {incr i} {
	if {($tabTransition($tpn(courant),$i,statut)==$ok)&&($i!=$laTransition)} {
	    if {$tabTransition($tpn(courant),$i,id)==$identifier} {
		set result 0
	    }
	}
    }
    return $result
 }

proc existIdP {letpn identifier} {   
    global tabPlace tabTransition 
    global fin ok

    set result 0
    for {set i 1} {$tabPlace($letpn,$i,statut)!=$fin} {incr i} {
	if {$tabPlace($letpn,$i,statut)==$ok} {
	    if {$tabPlace($letpn,$i,id)==$identifier} {
		set result 1
	    }
        }
    }
    return $result
}

proc existIdT {letpn identifier} {   
    global tabPlace tabTransition 
    global fin ok

    set result 0
    for {set i 1} {$tabTransition($letpn,$i,statut)!=$fin} {incr i} {
	if {$tabTransition($letpn,$i,statut)==$ok} {
	    if {$tabTransition($letpn,$i,id)==$identifier} {
		set result 1
	    }
        }
    }
    return $result
}



proc indiceIdP {letpn identifier} {   
    global tabPlace tabTransition 
    global fin ok

    set result -1
    for {set i 1} {($tabPlace($letpn,$i,statut)!=$fin)&&($result==-1)} {incr i} {
	if {$tabPlace($letpn,$i,statut)==$ok} {
	    if {$tabPlace($letpn,$i,id)==$identifier} {
		set result $i
	    }
        }
    }
    return $result
}

proc indiceIdT {letpn identifier} {   
    global tabPlace tabTransition 
    global fin ok

    set result -1
    for {set i 1} {($tabTransition($letpn,$i,statut)!=$fin)&&($result==-1)} {incr i} {
	if {$tabTransition($letpn,$i,statut)==$ok} {
	    if {$tabTransition($letpn,$i,id)==$identifier} {
		set result $i
	    }
        }
    }
    return $result
}

proc markingValide {marking taille} {
    # [entier [retirerListeCar $marking  [list , " "]]] On eneleve les , et on verifie que c'est un entier
    # On verifie qu'il y le bon nombre de nombres [split $marking ,]]==$taille
    if {[entier [retirerListeCar $marking  [list , " "]]]&&([llength [split $marking ,]]==$taille)} {
	    return 1
	} else {
	    return 0
    }
}


proc ajusterTaillePoids {marking taille} {

    set justeLesPoids [split $marking ,]
    set tailleActuelle [llength $justeLesPoids]
    
    if {$tailleActuelle>$taille} {
	set justeLesPoids [lappend [lrange $justeLesPoids 0 $taille-2] [lindex $justeLesPoids end]]
    } elseif {$tailleActuelle<$taille} {
#	set valeurAny [lindex $justeLesPoids end]
#	set justeLesPoids [lreplace $justeLesPoids end end] 0
	for {set i [expr $tailleActuelle-1]} {$i<$taille} {incr i} {
	    set justeLesPoids  [linsert $justeLesPoids end-1 0]
	}
#	set justeLesPoids  [linsert $justeLesPoids end-1 $valeurAny]
    }
    return $justeLesPoids
}


proc ajusterTailleMarking {marking taille} {

    set justeLesToken [split $marking ,]
    set tailleActuelle [llength $justeLesToken]

    if {$tailleActuelle==0} {
	set justeLesToken "O"
    }
    
    if {$taille<=1} {
	for {set i 1} {$i<$tailleActuelle} {incr i} {
	    set justeLesToken  [linsert $justeLesToken [expr 2*$i-1] +]
	}
	set justeLesToken [expr [sansEspace $justeLesToken]]
	
	if {$justeLesToken==""} {
	    set justeLesToken 0
	}
    } else {
	if {$tailleActuelle>$taille} {
	    set justeLesToken [lrange $justeLesToken 0 $taille-1]
	} elseif {$tailleActuelle<$taille} {
	    for {set i [expr $tailleActuelle]} {$i<$taille} {incr i} {
		set justeLesToken  [linsert $justeLesToken end 0]
	    }
	}
	for {set i 1} {$i<$taille} {incr i} {
	    set justeLesToken  [linsert $justeLesToken [expr 2*$i-1] ,]
	}
    }
    
    
    return [sansEspace $justeLesToken]
}


proc ajusterLesCouleurs {nbCouleurs letpn} {
    global tabPlace InitialToken ok fin
    global tabTransition allowedArc controle
    
    for {set i 1} {$tabTransition($letpn,$i,statut)!=$fin}  {incr i} {
	if {$tabTransition($letpn,$i,statut) == $ok} {
	   for {set j 1} {$tabTransition($letpn,$i,Porg,$j) >0}   {incr j} {
	       set typeArcValide 1 
	       if {(($tabTransition($letpn,$i,PorgType,$j)==1)&&($allowedArc(reset)==0))||(($tabTransition($letpn,$i,PorgType,$j)==2)&&($allowedArc(read)==0))||(($tabTransition($letpn,$i,PorgType,$j)==3)&&($allowedArc(logicInhibitor)==0))||(($tabTransition($letpn,$i,PorgType,$j)==4)&&(($allowedArc(timedInhibitor)==0)||($controle==1)))} {
		   set typeArcValide 0 
	       }
	       if {$typeArcValide} {
		   if {$tabTransition($letpn,$i,PorgTokenColor,$j)> [expr $nbCouleurs-1]} {
		       set tabTransition($letpn,$i,PorgTokenColor,$j) [expr $nbCouleurs-1]
		   }
	       }
	   }
	    for {set j 1} {$tabTransition($letpn,$i,Pdes,$j) >0}   {incr j} {

		if {$tabTransition($letpn,$i,PdesTokenColor,$j)>[expr $nbCouleurs-1]} {
		   set tabTransition($letpn,$i,PdesTokenColor,$j) [expr $nbCouleurs-1]
	       }
	   }
	   
       }
   }
   
}


proc forAllAjusterTailleMarking {taille letpn} {
    global tabPlace InitialToken ok fin
    global tabTransition allowedArc controle
    
   for {set i 1} {$tabPlace($letpn,$i,statut)!=$fin} {incr i} {
	if {$tabPlace($letpn,$i,statut)==$ok} {
	    set tabPlace($letpn,$i,jeton) [ajusterTailleMarking $tabPlace($letpn,$i,jeton) $taille]
	}
   }
   
 
}
