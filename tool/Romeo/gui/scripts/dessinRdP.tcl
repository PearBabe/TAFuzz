# This file is part of the RomÃ©o model-checking software
# 
# Copyright University of Nantes, Ã‰cole Centrale de Nantes, IRCCyN
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

# TODO TYPE   supprimerArcPlaceTransition ajouterNoeudPT ajouterNoeudPT


# la procedure redessiner le rdp
# les procedure associées au différentes actions sur les tags :
#                   release plotDown, plotMove
# sur les places, transitions, fleches, noeuds (coudes)
# le double click est dans maniTPN

proc redessinerLeTPNCourant {}  {
    global  projet tpn tabUnDo

    if {[retrouverMasterSlave]>0} {
	set leSlave [retrouverMasterSlave]
	redessinerRdP .romeo.global.slave.slave$leSlave.dessin.c
    } else {
	redessinerRdP .romeo.global.frame.c
    }
}




proc MAJdessinsProjetcourant {w} {

    global tabPlace projet
    global tpn tabUnDo
   
    global projet

    set kprim 1
    modifTPN $tpn(courant) 
    set tpn(courant) [calculTPNCourant 0]
    redessinerRdP $w.frame.c
    for {set i 1} {$i<=$projet($tpn(onglet),nbInput)}  {incr i} {
	if {$projet($tpn(onglet),input,$i,status) == "open"} {
	    set tpn(courant) [calculTPNCourant $i]
	    redessinerRdP $w.slave.slave$i.dessin.c
	}
    }
    set tpn(courant) [calculTPNCourant 0]

}


proc redessinerProjet {w} {

    global tabPlace projet
    global tpn tabUnDo
   
    global projet

    set kprim 1

    set tpn(courant) [calculTPNCourant 0]
    canvasAsc $w $w.frame.c
    if {$projet($tpn(onglet),nbInput)>0} {
	slaveCanvas $w $projet($tpn(onglet),nbOpen) 
    } else {
	if {[winfo exists $w.slave]} {
       destroy $w.slave
    }

    }
    set tpn(courant) [calculTPNCourant 0]

}

# **************** REDESSINER le RDP ***********************

proc redessinerRdP {c} {

    global tabPlace
    global tpn tabUnDo 
    global tabColor
    global tabTransition
    global tabNoeud
    global tabFlechePT
    global tabFlecheTP
    global fin
    global ok
    global destroy
    global nbProcesseur
    global parameters synchronized typePN cost controle
    global cTPN_FirableTransList cTPN_EnabledTransList cTPN_FirableColoredTwiceTransList  cTPN_FirableTransListPerColor
    global infini francais
    global select
    global zoom viewOnglet
    global quadrillage
    global simulatorOn
    global dimension
    global deltX
    global deltY
    global xArrow
    global yArrow
    global allowedArc
    global hideGU
    global semExclusionDessin maxX maxY


    
    set doitagain 0


   set zoom $viewOnglet(zoom,$tpn(onglet))

  if {($semExclusionDessin==1)&&[winfo exists $c]} {
    set semExclusionDessin 0
    set kprim 1
    $c delete all

    set slave [retrouverMasterSlaveFromCanvas $c]
    set tpn(courant) [calculTPNCourant $slave]

    set underscore "_"

#puts "$c , $tpn(courant) , $tpn(onglet)"

    if {$simulatorOn==0} {grille $c}

    #tk scaling $c 2

    #taille des éléments
    # rayon des places
    set r $dimension(place)
    # largeur des transitions
    set l $dimension(largeurTransition)
    # hauteur des transitions
    set h $dimension(hauteurTransition)
    # rayon des jetons
    set rj $dimension(jeton)
    # taille du noeud
    set hn $dimension(noeud)
    # taille du flush
    set fl $dimension(flush)
    

    set taillefont [expr int(-12*$zoom)]
    set taillefontPetit [expr int(-9*$zoom)]
    
    font configure font1 -family Times -size $taillefont
    font configure fontPetit -family Times -size $taillefontPetit



    #++++++++++++++++++++++++++ DESSIN DES ARCS  +++++++++++++++++++++++++++++++++++++

    #+++++++++++++++ Fleche Place vers transition +++++++++++++++

    set k 1
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {

     if {$tabTransition($tpn(courant),$i,statut) == $ok} {
      set type [expr $tabTransition($tpn(courant),$i,unctrl)]

      for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} {
	    set laCouleur $tabColor(Arc,$tabTransition($tpn(courant),$i,PorgColor,$j))
	    if {$simulatorOn} {if {[firable $slave$underscore$i]} {set laCouleur blue} }

        set arrow 1
        set offset 0
        set typeArcValide 1
	

        if {$tabTransition($tpn(courant),$i,PorgType,$j)>0} {
		  set arrow 0
		  if {$tabTransition($tpn(courant),$i,PorgType,$j)==3} {set offset 2} 
		  if {$tabTransition($tpn(courant),$i,PorgType,$j)==2} {set offset 1} 
		  if {$tabTransition($tpn(courant),$i,PorgType,$j)==4} {set offset -1} 
		  if {$tabTransition($tpn(courant),$i,PorgType,$j)==1} {set offset -2} 
	          if {(($tabTransition($tpn(courant),$i,PorgType,$j)==1)&&($allowedArc(reset)==0))||(($tabTransition($tpn(courant),$i,PorgType,$j)==2)&&($allowedArc(read)==0))||(($tabTransition($tpn(courant),$i,PorgType,$j)==3)&&($allowedArc(logicInhibitor)==0))||(($tabTransition($tpn(courant),$i,PorgType,$j)==4)&&(($allowedArc(timedInhibitor)==0)||($controle==1)))} {
		      set typeArcValide 0 
                  }
        }
	  if {$typeArcValide} {
        
		if {$tabTransition($tpn(courant),$i,PorgNailx,$j)+$tabTransition($tpn(courant),$i,PorgNaily,$j)==0} {

		   set xa $tabPlace($tpn(courant),$tabTransition($tpn(courant),$i,Porg,$j),xy,x)
		   set ya $tabPlace($tpn(courant),$tabTransition($tpn(courant),$i,Porg,$j),xy,y)
		   set xb $tabTransition($tpn(courant),$i,xy,x)
		   set yb $tabTransition($tpn(courant),$i,xy,y)

		   set motifFleche [faireUnArcPT $c $xa $ya $xb $yb $laCouleur $arrow $type $offset]
                   set xWeight [moyMax $xa $xb] 
                   set yWeight [moyMax $yb $ya]
		  
		} else {
		    set xa $tabPlace($tpn(courant),$tabTransition($tpn(courant),$i,Porg,$j),xy,x)
		    set ya $tabPlace($tpn(courant),$tabTransition($tpn(courant),$i,Porg,$j),xy,y)
		    set xb $tabTransition($tpn(courant),$i,PorgNailx,$j)
		    set yb $tabTransition($tpn(courant),$i,PorgNaily,$j)
		    set xc $tabTransition($tpn(courant),$i,xy,x)
		    set yc $tabTransition($tpn(courant),$i,xy,y)
  
  		    set motifFleche [faireUnArcPnT $c $xa $ya $xb $yb $xc $yc $laCouleur $arrow $type $offset]
		    
		    # puis on met le noeud
		    set motifNoeud [$c create rect [expr $xb-$hn] [expr $yb-$hn] \
					[expr $xb+$hn] [expr $yb+$hn] -width 1 -outline black \
					-fill green]

		    $c addtag noeud($kprim) withtag $motifNoeud

		    $c bind noeud($kprim) <Any-Enter> "anyEnter $c"
		    $c bind noeud($kprim) <Any-Leave> "anyLeaveNoeud $c $kprim"
		    $c bind noeud($kprim) <1> "plotDownNoeud $c %x %y $kprim $slave"
		    $c bind noeud($kprim) <ButtonRelease-1> "releaseNoeud $c %x %y $kprim"
		    $c bind noeud($kprim) <B1-Motion> "plotMoveNoeud $c %x %y $kprim"
		    $c bind noeud($kprim) <Double-Button-1> "doubleClickFPT $c $k $slave"

		    set tabNoeud($kprim,TP) -1
		    set tabNoeud($kprim,arc) $k

		    # pour placer le weight on fait le changement :
		    #y = ax+b avec a = ($yc-$ya)/($xc-$xa) b pour ($xc,$yc)
		    #on cherche si b est au dessus de la droite passant par a et c

  	            if {$xc==$xa} {
		       set coef [signe [expr $yb-((($yc-$ya)/(0.001))*($xb-$xc)+$yc)]]
                    } else {
                        set coef [signe [expr $yb-((($yc-$ya)/($xc-$xa))*($xb-$xc)+$yc)]]
                    }

   		    set xWeight [expr $xb-$coef*7]  
		    set yWeight [expr $yb+$coef*5]
		    incr kprim
		}


		# pour tous les arcs PT (avec ou sans noeud) avec ou sans flush :

#+++++++++++++DESSIN DU FLUSH READ INHIBITOR++++++++++++++++++++++++++++++++++++++
		
	    set InhibCond ""
            if {$tabTransition($tpn(courant),$i,PorgType,$j)==1} {
			 set motifFlush [$c create polygon [expr $xArrow + $fl] $yArrow \
					    [expr $xArrow] [expr $yArrow + $fl] [expr $xArrow - $fl] [expr $yArrow] \
					    [expr $xArrow] [expr $yArrow - $fl] -width 1 -outline black -fill black]  
			 $c addtag flush($i,$j) withtag $motifFlush   
             } elseif {$tabTransition($tpn(courant),$i,PorgType,$j)==2} {
			 set motifRead [$c create polygon [expr $xArrow - $fl] [expr $yArrow - $fl] \
					    [expr $xArrow  + $fl] [expr $yArrow - $fl] [expr $xArrow + $fl] [expr $yArrow + $fl] \
					    [expr $xArrow - $fl] [expr $yArrow + $fl]  -width 1 -outline black -fill lightgray]  
			 $c addtag readArc($i,$j) withtag $motifRead   
             } elseif {$tabTransition($tpn(courant),$i,PorgType,$j)==3} {
			 set motifLogicInhib [$c create oval [expr $xArrow - $fl] [expr $yArrow - $fl] [expr $xArrow + $fl] [expr $yArrow + $fl] -width .5 -outline black -fill orange]  
			 $c addtag logicInhib($i,$j) withtag $motifLogicInhib   
             } elseif {$tabTransition($tpn(courant),$i,PorgType,$j)==4} {
			 set motifTimedInhib [$c create oval [expr $xArrow - $fl] [expr $yArrow - $fl] [expr $xArrow + $fl] [expr $yArrow + $fl] -width 2 -outline black -fill white]  
			 $c addtag timedInhib($i,$j) withtag $motifTimedInhib   
		         set InhibCond  $tabTransition($tpn(courant),$i,PorgInhibitingCondition,$j)
            }


		$c addtag flechePT($k) withtag $motifFleche
		set tabFlechePT($k,place) $tabTransition($tpn(courant),$i,Porg,$j)
		set tabFlechePT($k,transition) $i
		set tabFlechePT($k,type) $tabTransition($tpn(courant),$i,PorgType,$j)

		$c bind flechePT($k)  <Any-Enter> "anyEnter $c"
		$c bind flechePT($k) <Any-Leave> "anyLeaveArc $c $tabTransition($tpn(courant),$i,PorgColor,$j)"
		$c bind flechePT($k) <1> "plotDownFPT $c %x %y $k $slave"
		$c bind flechePT($k) <Button-3> "clickDroitFPT $c %x %y $k $slave"
		$c bind flechePT($k) <Button-2> "doubleClickFPT $c $k $slave"
		$c bind flechePT($k) <Double-Button-1> "doubleClickFPT $c $k $slave"

		if {($tabTransition($tpn(courant),$i,PorgWeight,$j)!=1)||($InhibCond!="")} {
		    	if {($InhibCond!="")} {
			    	if {($tabTransition($tpn(courant),$i,PorgWeight,$j)!=1)} {
				    set InhibCond "$tabTransition($tpn(courant),$i,PorgWeight,$j), \n $InhibCond"
				}
			} else {
			    set InhibCond "$tabTransition($tpn(courant),$i,PorgWeight,$j)"
			}
	
		    set motifWeight [$c create text $xWeight $yWeight \
					 -text $InhibCond -fill green4 -font font1 -anchor center]
		    $c addtag labelPTWeight($k) withtag $motifWeight
		    $c bind labelPTWeight($k)  <Any-Enter> "anyEnter $c"
		    $c bind labelPTWeight($k) <Any-Leave> "anyLeaveWeight $c"
		    $c bind labelPTWeight($k) <Double-Button-1> "doubleClickWeight $c $k $slave"
		    $c bind labelPTWeight($k) <1> "plotDownWeight $c %x %y $k $slave"
		    $c bind labelPTWeight($k) <ButtonRelease-1> "releaseWeight $c %x %y $k"
		    $c bind labelPTWeight($k) <B1-Motion> "plotMoveWeight $c %x %y $k"




		}

		incr k

	    }
	}
	}
    }
    set tabFlechePT($k,transition) -1
    set tabFlechePT($k,place) -1
    set tabFlechePT($k,type) 0

    #+++++++++++++++ Fleche transition vers place +++++++++++++++

    set k 1
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {

      if {$tabTransition($tpn(courant),$i,statut) == $ok} {
	  set arrow -1
	  set type  [expr $tabTransition($tpn(courant),$i,unctrl)]

          for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} {
	    set laCouleur $tabColor(Arc,$tabTransition($tpn(courant),$i,PdesColor,$j))
	    if {$simulatorOn} {if {[firable $slave$underscore$i]} {set laCouleur brown} }
		if {$tabTransition($tpn(courant),$i,PdesNailx,$j)+$tabTransition($tpn(courant),$i,PdesNaily,$j)==0} {
		    set xa $tabTransition($tpn(courant),$i,xy,x)
		    set ya $tabTransition($tpn(courant),$i,xy,y)
		    set xb $tabPlace($tpn(courant),$tabTransition($tpn(courant),$i,Pdes,$j),xy,x)
		    set yb $tabPlace($tpn(courant),$tabTransition($tpn(courant),$i,Pdes,$j),xy,y)


		    set motifFleche [faireUnArcPT $c $xb $yb $xa $ya $laCouleur $arrow $type 0]
		    set xWeight [moyMax $xa $xb] 
		    set yWeight [moyMax $yb $ya]
		} else {
		    set xc $tabPlace($tpn(courant),$tabTransition($tpn(courant),$i,Pdes,$j),xy,x)
		    set yc $tabPlace($tpn(courant),$tabTransition($tpn(courant),$i,Pdes,$j),xy,y)
		    set xb $tabTransition($tpn(courant),$i,PdesNailx,$j)
		    set yb $tabTransition($tpn(courant),$i,PdesNaily,$j)
		    set xa $tabTransition($tpn(courant),$i,xy,x)
		    set ya $tabTransition($tpn(courant),$i,xy,y)

 		    set motifFleche [faireUnArcPnT $c $xc $yc $xb $yb $xa $ya $laCouleur $arrow $type 0]

		    # puis on met le noeud
		    set motifNoeud [$c create rect [expr $xb-$hn] [expr $yb-$hn] \
					[expr $xb+$hn] [expr $yb+$hn] -width 1 -outline black \
					-fill green]
		    $c addtag noeud($kprim) withtag $motifNoeud
		    $c bind noeud($kprim) <Any-Enter> "anyEnter $c"
		    $c bind noeud($kprim) <Any-Leave> "anyLeaveNoeud $c $kprim"
		    $c bind noeud($kprim) <ButtonRelease-1> "releaseNoeud $c %x %y $kprim"
		    $c bind noeud($kprim) <1> "plotDownNoeud $c %x %y $kprim $slave"
		    $c bind noeud($kprim) <B1-Motion> "plotMoveNoeud $c %x %y $kprim"
		    set tabNoeud($kprim,TP) 1
		    set tabNoeud($kprim,arc) $k

		    incr kprim

		    # pour placer le weight on fait le changement :
		    #y = ax+b avec a = ($yc-$ya)/($xc-$xa) b pour ($xc,$yc)
		    #on cherche si b est au dessus de la droite passant par a et c

  	        if {$xc==$xa} {
		       set coef [signe [expr $yb-((($yc-$ya)/(0.001))*($xb-$xc)+$yc)]]
            } else {
               set coef [signe [expr $yb-((($yc-$ya)/($xc-$xa))*($xb-$xc)+$yc)]]
            }

   		    set xWeight [expr $xb-$coef*7]  
		    set yWeight [expr $yb+$coef*5]

		}


# To be continued -------------------------------------------------------------------------------------------------
#A mettre en haut : 

#	    if {$tabTransition($tpn(courant),$numTransition,unctrl)} {
#			 set motifFlush [$c create polygon [expr $xArrow + $fl] $yArrow \
#					    [expr $xArrow] [expr $yArrow + $fl] [expr $xArrow - $fl] [expr $yArrow] \
#					    [expr $xArrow] [expr $yArrow - $fl] -width 1 -outline black -fill black]  
#			 $c addtag flush($i,$j) withtag $motifFlush 
#	    }


		# pour tous les arcs PT (avec ou sans noeud) :

		$c addtag flecheTP($k) withtag $motifFleche
		set tabFlecheTP($k,place) $tabTransition($tpn(courant),$i,Pdes,$j)
		set tabFlecheTP($k,transition) $i
		$c bind flecheTP($k)  <Any-Enter> "anyEnter $c"
		$c bind flecheTP($k) <Any-Leave> "anyLeaveArc $c $tabTransition($tpn(courant),$i,PdesColor,$j)"
		$c bind flecheTP($k) <1> "plotDownFTP $c %x %y $k $slave"
		$c bind flecheTP($k) <Button-3> "clickDroitFTP $c %x %y $k $slave"
		$c bind flecheTP($k) <Button-2> "doubleClickFTP $c $k $slave"
		$c bind flecheTP($k) <Double-Button-1> "doubleClickFTP $c $k $slave"

		if {$tabTransition($tpn(courant),$i,PdesWeight,$j)!=1} {
		    set motifWeight [$c create text $xWeight $yWeight \
					 -text $tabTransition($tpn(courant),$i,PdesWeight,$j) -fill green4 -font font1 -anchor center]
		    $c addtag labelTPWeight($k) withtag $motifWeight
		    $c bind labelTPWeight($k)  <Any-Enter> "anyEnter $c"
		    $c bind labelTPWeight($k) <Any-Leave> "anyLeaveWeight $c"
		    $c bind labelTPWeight($k) <Double-Button-1> "doubleClickFTP $c $k $slave"
		    $c bind labelTPWeight($k) <Button-3> "doubleClickFTP $c $k $slave"
		}

		incr k

	    }
	}
    }
    set tabNoeud($kprim,arc) -1
    set tabFlecheTP($k,transition) -1
    set tabFlecheTP($k,place) -1



    #++++++++++++++++++++++++++ DESSIN DES PLACES  +++++++++++++++++++++++++++++++++++++

    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
	if {$tabPlace($tpn(courant),$i,statut)==$ok} {
	    set x $tabPlace($tpn(courant),$i,xy,x)
	    set y $tabPlace($tpn(courant),$i,xy,y)

	    if {$x*$zoom> $maxX} {
		set maxX [expr {round($x*$zoom)+100}]
		set doitagain 1
	    }
	    if {$y*$zoom> $maxY} {
		set maxY [expr {round($y*$zoom)+100}]
		set doitagain 1
	    }
	    
	    if {$simulatorOn==0} {set laCouleur $tabColor(Place,$tabPlace($tpn(courant),$i,color)) 
	    } elseif {[nulMarking $tabPlace($tpn(courant),$i,jeton)]} { set laCouleur lightGray} else {set laCouleur yellow}
	    
	    set motifPlace [$c create oval [expr $x-$r] [expr $y-$r] \
				[expr $x+$r] [expr $y+$r] -width 1 -outline black \
				-fill $laCouleur]

	    $c addtag place($i) withtag $motifPlace 

	    $c bind place($i) <Any-Enter> "anyEnterPlace $c $i"
	    $c bind place($i) <Any-Leave> "anyLeavePlace $c $i $laCouleur"
	    $c bind place($i) <1> "plotDownP $c %x %y $i $slave"
	    $c bind place($i) <Double-Button-1> "doubleClickP $c $i $slave"
	    $c bind place($i) <Control-Button-1> "ctrlClickP $c %x %y $i $slave"
	    $c bind place($i) <Button-3> "clickDroitP $c %x %y $i $slave"
	    $c bind place($i) <Button-2> "clickDroitP $c %x %y $i $slave"
	    $c bind place($i) <ButtonRelease-1> "releasePlace $c %x %y $i"
	    $c bind place($i) <ButtonRelease-2> "releasePlace $c %x %y $i"
	    $c bind place($i) <ButtonRelease-3> "releasePlace $c %x %y $i"
	    $c bind place($i) <B1-Motion> "plotMovePlace $c %x %y $i"

	    
	    if {[nulMarking $tabPlace($tpn(courant),$i,jeton)]==0} {
		set motifJeton [$c create oval [expr $x-$rj+3] [expr $y-$rj] \
				    [expr $x+$rj+3] [expr $y+$rj] -width 1  -outline black \
				    -fill black]
		set texteJeton [$c create text $x $y -text $tabPlace($tpn(courant),$i,jeton) -fill black -font fontPetit -anchor e]
		$c addtag jet($i) withtag $motifJeton 
		$c addtag jet($i) withtag $texteJeton 
		
		$c bind jet($i) <Any-Enter> "anyEnterPlace $c $i"
		$c bind jet($i) <Any-Leave> "anyLeavePlace $c $i $laCouleur"
		$c bind jet($i) <1> "plotDownP $c %x %y $i $slave"
		$c bind jet($i) <Button-2> "clickDroitP $c %x %y $i $slave"
		$c bind jet($i) <Button-3> "clickDroitP $c %x %y $i $slave"
		$c bind jet($i) <Control-Button-1> "ctrlClickP $c %x %y $i $slave"
		$c bind jet($i) <ButtonRelease-1> "releasePlace $c %x %y $i"
		$c bind jet($i) <ButtonRelease-2> "releasePlace $c %x %y $i"
		$c bind jet($i) <ButtonRelease-3> "releasePlace $c %x %y $i"
		$c bind jet($i) <B1-Motion> "plotMovePlace $c %x %y $i"
		$c bind jet($i) <Double-Button-1> "doubleClickP $c $i $slave"
	    }  
	    
	    # creation du tag label Place
	    if {!$hideGU(Plabel)} {
		if {($tabPlace($tpn(courant),$i,label,nom) !=  $tabPlace($tpn(courant),$i,id))&&(!$hideGU(Pidentifier))} {
		    set nomPlaceAff "$tabPlace($tpn(courant),$i,label,nom) ( $tabPlace($tpn(courant),$i,id) )"
		} else {
		    set nomPlaceAff "$tabPlace($tpn(courant),$i,label,nom)"
		}
	    } elseif {!$hideGU(Pidentifier)} {
		    set nomPlaceAff "( $tabPlace($tpn(courant),$i,id) )"
	    } else {
		    set nomPlaceAff ""
	    }
	    if {$tabPlace($tpn(courant),$i,processeur)>$nbProcesseur($tpn(courant))} {set tabPlace($tpn(courant),$i,processeur) 0}
	    if {($tabPlace($tpn(courant),$i,processeur)>0)&&($typePN==-2)&&($controle!=1)} {
		set leTexte "$nomPlaceAff \n Proc. $tabPlace($tpn(courant),$i,processeur) \n Prio. $tabPlace($tpn(courant),$i,priorite)"
	    } else {
		if {($typePN==2)&&(!(($tabPlace($tpn(courant),$i,dmin)==0) && ($tabPlace($tpn(courant),$i,dmax)== $infini)))&&($controle!=1)} {
		    if {$tabPlace($tpn(courant),$i,dmax) < $infini} {
			set finInterval "$tabPlace($tpn(courant),$i,dmax) \]"
		    } else {
			set finInterval "inf \["
		    }
		    set leTexte "$nomPlaceAff \n \[ $tabPlace($tpn(courant),$i,dmin); $finInterval"
		 } else { set leTexte $nomPlaceAff }
	    }

	    set motifLabel [$c create text [expr $x+$tabPlace($tpn(courant),$i,label,dx)] \
				[expr $y+$tabPlace($tpn(courant),$i,label,dy)] -text $leTexte -fill blue4 -font font1 -anchor n]
	    $c addtag labelPlace($i) withtag $motifLabel
	    $c bind labelPlace($i) <Any-Enter> "anyEnter $c"
	    $c bind labelPlace($i) <Any-Leave> "anyLeaveLabelPlace $c $i"
	    $c bind labelPlace($i) <1> "plotDownLabelPlace $c %x %y $i $slave"
	    $c bind labelPlace($i) <Button-2> "clickDroitP $c %x %y $i $slave"
	    $c bind labelPlace($i) <Button-3> "clickDroitP $c %x %y $i $slave"
	    $c bind labelPlace($i) <ButtonRelease-1> "releaseLabelPlace $c %x %y $i"
	    $c bind labelPlace($i) <ButtonRelease-2> "releaseLabelPlace $c %x %y $i"
	    $c bind labelPlace($i) <ButtonRelease-3> "releaseLabelPlace $c %x %y $i"
	    $c bind labelPlace($i) <B1-Motion> "plotMoveLabelPlace $c %x %y $i"
	    $c bind labelPlace($i) <Double-Button-1> "doubleClickP $c $i $slave"


	}
    }

    #++++++++++++++++++++++++++ DESSIN DES TRANSITIONS  ++++++++++++++++++++++++++++++++ ICI

    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
	if {$tabTransition($tpn(courant),$i,statut) == $ok} {
	    set x $tabTransition($tpn(courant),$i,xy,x)
	    set y $tabTransition($tpn(courant),$i,xy,y)

	    if {$x*$zoom> $maxX} {
		set maxX [expr {round($x*$zoom)+100}]
		set doitagain 1
	    }
	    if {$y*$zoom> $maxY} {
		set maxY [expr {round($y*$zoom)+100}]
		set doitagain 1
	    }

	    
#	    if {[isSynchronized $i]}  

	    if {$tabTransition($tpn(courant),$i,priority)!=0} {
		set epaisseur 3
	    } else { 
		set epaisseur 1
	    }
	    if {$simulatorOn==0} {set laCouleur $tabColor(Transition,$tabTransition($tpn(courant),$i,color))  
	    } elseif {[firable $slave$underscore$i]==1} {
		if {[firableTwice $slave$underscore$i]==1} {
		    set laCouleur orange
		} else {
		    set laCouleur $tabColor(simulator,firableTrans)
		}
	    } elseif {[enabled $slave$underscore$i]==1} {set laCouleur $tabColor(simulator,enabledTrans)
	    } else {set laCouleur $tabColor(simulator,noEnabledTrans)}
	    

	    if {($controle>=1)&&($tabTransition($tpn(courant),$i,unctrl) >= 1)} {
		set motifTransition [$c create rect [expr $x-$l] [expr $y-$h] \
				     [expr $x+$l] [expr $y+$h] -outline black -width 2 -dash {2 4} \
				     -fill $laCouleur]
	    } else {
		set motifTransition [$c create rect [expr $x-$l] [expr $y-$h] \
				     [expr $x+$l] [expr $y+$h] -width $epaisseur -outline black \
				     -fill $laCouleur]
	    }
	    $c addtag transition($i) withtag $motifTransition

	    $c bind transition($i) <Any-Enter> "anyEnterTransition  $c $i"
	    $c bind transition($i) <Any-Leave> "anyLeaveTransition $c $i $laCouleur"
	    $c bind transition($i) <1> "plotDownT $c %x %y $i $slave"
	    $c bind transition($i) <Double-Button-1> "doubleClickT $c $i $slave"
	    $c bind transition($i) <Button-2> "doubleClickT $c $i $slave"
	    $c bind transition($i) <Button-3> "doubleClickT $c $i $slave"
	    $c bind transition($i) <ButtonRelease-1> "releaseTransition $c %x %y $i"
	    $c bind transition($i) <ButtonRelease-2> "releaseTransition $c %x %y $i"
	    $c bind transition($i) <ButtonRelease-3> "releaseTransition $c %x %y $i"
	    $c bind transition($i) <B1-Motion> "plotMoveTransition $c %x %y $i"

	    # creation du tag label transition
	    if {!$hideGU(Tlabel)} {
		if {($tabTransition($tpn(courant),$i,label,nom) !=  $tabTransition($tpn(courant),$i,id))&&(!$hideGU(Tidentifier))} {
		    set leTexte "$tabTransition($tpn(courant),$i,label,nom) ( $tabTransition($tpn(courant),$i,id) )"
		} else {
		    set leTexte "$tabTransition($tpn(courant),$i,label,nom)"
		}
	    } elseif {!$hideGU(Tidentifier)} {
		     set leTexte $tabTransition($tpn(courant),$i,id)
	    } else {
		    set leTexte ""
	    }

	    if {($controle!=1)&&($typePN!=0)} {
	      if {$parameters>=1} {
		if {$tabTransition($tpn(courant),$i,minparam)!= ""} {
			set min $tabTransition($tpn(courant),$i,minparam)
                } else {set min 0}
		  if {$tabTransition($tpn(courant),$i,maxparam)!= ""} {
		      if {$controle>=1} {
			  set finInterval "$tabTransition($tpn(courant),$i,maxparam) \]"
		      } else {
			  set finInterval "$tabTransition($tpn(courant),$i,maxparam) [crochetOF 0 $tabTransition($tpn(courant),$i,lftIncl)]"
		      }

		      if {![string compare $tabTransition($tpn(courant),$i,maxparam) "infinity"]} {set finInterval  "inf )"}
		  } else {
		      set finInterval  "inf )"
		  }

		  if {$controle>=1} {
		      set debutInterval "\[ $min;"
		  } else {
		      set debutInterval "[crochetOF 1 $tabTransition($tpn(courant),$i,eftIncl)] $min;"
		  }

		  if {!(($min == 0)&&($tabTransition($tpn(courant),$i,eftIncl)==1) && (![string compare $finInterval "inf )" ]))} {
		      set leTexte "$leTexte \n $debutInterval $finInterval"
                }

	      } else {

		  if {($typePN!=2)&&(!(($tabTransition($tpn(courant),$i,dmin)==0) && ($tabTransition($tpn(courant),$i,dmax)== $infini)&&($tabTransition($tpn(courant),$i,eftIncl)==1)))} {

		      if {$controle>=1} {
			  set debutInterval "\[ $tabTransition($tpn(courant),$i,dmin);"
		      } else {
			  set debutInterval "[crochetOF 1 $tabTransition($tpn(courant),$i,eftIncl)] $tabTransition($tpn(courant),$i,dmin);"
		      }
		      
		      if {$tabTransition($tpn(courant),$i,dmax) < $infini} {

			  if {$controle>=1} {
			      set finInterval "$tabTransition($tpn(courant),$i,dmax) \]"
			  } else {
			      set finInterval "$tabTransition($tpn(courant),$i,dmax) [crochetOF 0 $tabTransition($tpn(courant),$i,lftIncl)]"
			  }

		    } else {
				set finInterval "inf )"
			}
			set leTexte "$leTexte \n $debutInterval $finInterval"
		}
	      }
	    }	    
	    set motifLabel [$c create text  [expr $x+$tabTransition($tpn(courant),$i,label,dx)] \
				[expr $y+$tabTransition($tpn(courant),$i,label,dy)] -text $leTexte -fill darkgoldenrod4 -font font1 -anchor n]
	    $c addtag labelTransition($i) withtag $motifLabel
	    $c bind labelTransition($i) <Any-Enter> "anyEnter $c"
	    $c bind labelTransition($i) <Any-Leave> "anyLeaveLabelTransition $c $i"
	    $c bind labelTransition($i) <1> "plotDownLabelTransition $c %x %y $i $slave"
	    $c bind labelTransition($i) <Double-Button-1> "doubleClickT $c $i $slave"
	    $c bind labelTransition($i) <Button-2> "doubleClickT $c $i $slave"
	    $c bind labelTransition($i) <Button-3> "doubleClickT $c $i $slave"
	    $c bind labelTransition($i) <ButtonRelease-1> "releaseLabelTransition $c %x %y $i"
	    $c bind labelTransition($i) <ButtonRelease-2> "releaseLabelTransition $c %x %y $i"
	    $c bind labelTransition($i) <ButtonRelease-3> "releaseLabelTransition $c %x %y $i"
	    $c bind labelTransition($i) <B1-Motion> "plotMoveLabelTransition $c %x %y $i"
	    if {!$hideGU(guard)} {
		set leTexteGuard "$tabTransition($tpn(courant),$i,guard)"
		set motifGuard [$c create text  [expr $x+$tabTransition($tpn(courant),$i,guard,dx)] \
				[expr $y+$tabTransition($tpn(courant),$i,guard,dy)] -text $leTexteGuard -fill darkgreen -font font1 -anchor n]
		$c addtag guardTransition($i) withtag $motifGuard
		$c bind guardTransition($i) <Any-Enter> "anyEnter $c"
		$c bind guardTransition($i) <Double-Button-1> "doubleClickT $c $i $slave"
		$c bind guardTransition($i) <Button-2> "doubleClickT $c $i $slave"
		$c bind guardTransition($i) <Button-3> "doubleClickT $c $i $slave"
		$c bind guardTransition($i) <Any-Leave> "anyLeaveGuardTransition $c $i"
		$c bind guardTransition($i) <1> "plotDownGuardTransition $c %x %y $i $slave"
		$c bind guardTransition($i) <ButtonRelease-1> "releaseGuardTransition $c %x %y $i"
		$c bind guardTransition($i) <ButtonRelease-2> "releaseGuardTransition $c %x %y $i"
		$c bind guardTransition($i) <ButtonRelease-3> "releaseGuardTransition $c %x %y $i"
		$c bind guardTransition($i) <B1-Motion> "plotMoveGuardTransition $c %x %y $i"
	    }
	    if {!$hideGU(update)} {
		set leTexteUpdate "$tabTransition($tpn(courant),$i,update)"
		set motifUpdate [$c create text  [expr $x+$tabTransition($tpn(courant),$i,update,dx)] \
				[expr $y+$tabTransition($tpn(courant),$i,update,dy)] -text $leTexteUpdate -fill blue -font font1 -anchor n]
		$c addtag updateTransition($i) withtag $motifUpdate
		$c bind updateTransition($i) <Any-Enter> "anyEnter $c"
		$c bind updateTransition($i) <Double-Button-1> "doubleClickT $c $i $slave"
		$c bind updateTransition($i) <Button-2> "doubleClickT $c $i $slave"
		$c bind updateTransition($i) <Button-3> "doubleClickT $c $i $slave"
		$c bind updateTransition($i) <Any-Leave> "anyLeaveUpdateTransition $c $i"
		$c bind updateTransition($i) <1> "plotDownUpdateTransition $c %x %y $i $slave"
		$c bind updateTransition($i) <ButtonRelease-1> "releaseUpdateTransition $c %x %y $i"
		$c bind updateTransition($i) <ButtonRelease-2> "releaseUpdateTransition $c %x %y $i"
		$c bind updateTransition($i) <ButtonRelease-3> "releaseUpdateTransition $c %x %y $i"
		$c bind updateTransition($i) <B1-Motion> "plotMoveUpdateTransition $c %x %y $i"
	    }
	    if {($typePN==-3)&&($controle!=1)} {
		set leTexteSpeed "d\/dt=$tabTransition($tpn(courant),$i,speed)"
		set motifSpeed [$c create text  [expr $x+$tabTransition($tpn(courant),$i,speed,dx)] \
				[expr $y+$tabTransition($tpn(courant),$i,speed,dy)] -text $leTexteSpeed -fill DarkOrchid4 -font font1 -anchor n]
		$c addtag speedTransition($i) withtag $motifSpeed
		$c bind speedTransition($i) <Any-Enter> "anyEnter $c"
		$c bind speedTransition($i) <Double-Button-1> "doubleClickT $c $i $slave"
		$c bind speedTransition($i) <Button-2> "doubleClickT $c $i $slave"
		$c bind speedTransition($i) <Button-3> "doubleClickT $c $i $slave"
		$c bind speedTransition($i) <Any-Leave> "anyLeaveSpeedTransition $c $i"
		$c bind speedTransition($i) <1> "plotDownSpeedTransition $c %x %y $i $slave"
		$c bind speedTransition($i) <ButtonRelease-1> "releaseSpeedTransition $c %x %y $i"
		$c bind speedTransition($i) <ButtonRelease-2> "releaseSpeedTransition $c %x %y $i"
		$c bind speedTransition($i) <ButtonRelease-3> "releaseSpeedTransition $c %x %y $i"
		$c bind speedTransition($i) <B1-Motion> "plotMoveSpeedTransition $c %x %y $i"
	    }
	    if {($cost>0)&&($controle==0)} {
		set leTexteCost "cost=$tabTransition($tpn(courant),$i,cost)"
		set motifCost [$c create text  [expr $x+$tabTransition($tpn(courant),$i,cost,dx)] \
				[expr $y+$tabTransition($tpn(courant),$i,cost,dy)] -text $leTexteCost -fill VioletRed4 -font font1 -anchor n]
		$c addtag costTransition($i) withtag $motifCost
		$c bind costTransition($i) <Any-Enter> "anyEnter $c"
		$c bind costTransition($i) <Double-Button-1> "doubleClickT $c $i $slave"
		$c bind costTransition($i) <Any-Leave> "anyLeaveCostTransition $c $i"
		$c bind costTransition($i) <1> "plotDownCostTransition $c %x %y $i $slave"
		$c bind costTransition($i) <ButtonRelease-1> "releaseCostTransition $c %x %y $i"
		$c bind costTransition($i) <ButtonRelease-2> "releaseCostTransition $c %x %y $i"
		$c bind costTransition($i) <ButtonRelease-3> "releaseCostTransition $c %x %y $i"
		$c bind costTransition($i) <B1-Motion> "plotMoveCostTransition $c %x %y $i"
		$c bind costTransition($i) <Button-2> "doubleClickT $c $i $slave"
		$c bind costTransition($i) <Button-3> "doubleClickT $c $i $slave"
	    }


	}
    }

    if { $select(tpn) == $tpn(courant)} {
	set select(fenetre) $c
	set select(onglet) $tpn(onglet)
	recreerSelected $c
    }
    $c itemconfig selected -fill red
    $c scale all 0 0 $zoom $zoom 

    set font2 {Helvetica 4 bold}



      set semExclusionDessin 1

      if {$doitagain} {
	  destroy .romeo.global.frame
	  canvasAsc .romeo.global $c
	  redessinerRdP $c
      }

  }

    # fin de redessiner rdp
}

#*******************************************************************************************
# DESSIN DES ARCS (courbe de Bezier ....)
#*******************************************************************************************

#Dessine un arc entre une place A(xa,ya) et une transition B(xb,yb) orientée -1 0 ou 1

proc faireUnArcPT {c xa ya xb yb laCouleur arrow type offset} {
    global dimension
    global xArrow
    global yArrow
    global controle
    global nbTokenColor tpn zoom

        set offsetX 0
	set offsetY 0

            set r $dimension(place)
            set l $dimension(largeurTransition)
            set h $dimension(hauteurTransition)
            set fl $dimension(flush)

	# il faut maintenant retirer  a/sqrt(a*a+b*b) pour partir du cercle :
		    # le rayon du cercle est $r (8)
		    set hypo [expr hypot($xb-$xa, [expr $yb-$ya])]
		    if {$hypo==0} {set hypo 1}
		    set rx [expr ($xb-$xa)*$r/$hypo]
		    set ry [expr ($yb-$ya)*$r/$hypo]
		    set xa [expr $xa+$rx]
		    set ya [expr $ya+$ry]

		    # pour partir du bord de la transition
		    set den [expr $xa-$xb]
		    if {$den==0} {set den 1}
		    # delX et deltY pour faire le flush et les inhibitor....
		    set deltX -1
		    set deltY -1
		    if {[expr abs(($ya-$yb)/($den))]<0.3} {
 		      set offsetY $offset
			  if {$yb>$ya} { set deltY -1} else { set deltY 1}
			  if {$xb>$xa} { 
			    set xb [expr $xb-$l] 
			    set deltX -1
			  } else { 
			    set xb [expr $xb+$l] 
			    set deltX 1
			  }
		    } else {
		      set offsetX $offset
			  if {$xb>$xa} { set deltX -2} else { set deltX 2}
			  if {$yb>$ya} { 
			    set yb [expr $yb-$h] 
			    set deltY -1
			  } else { 
			    set yb [expr $yb+$h] 
			    set deltY 1
			  }
		    }

                   set xArrow [expr $xb + $fl*$deltX + $offsetX*$deltX] 
		   set yArrow [expr $yb + $fl*$deltY + $offsetY*$deltY] 
    

                   set avoidableDash {}
                   set unctrlDash {}
                   set epaisseur 1
                   set flecheNormal [list  [expr {7*$zoom}] [expr {12*$zoom}] [expr {4*$zoom}]]
                   set ineluctable $flecheNormal

		      #{6 12 4}
    #"\{[expr 6*$zoom] [expr 12*$zoom] [expr 12*$zoom] \}"
                   if {($controle > 1)&&($type>0)} {
		         set epaisseur 2
		         set unctrlDash {4 2}
		         set avoidableDash {2 4}
		   } elseif {$controle == 1} {
		       if {$type>0} {
		         set  epaisseur 1
		         set unctrlDash {6 4}
			 if {($type==2)||($type==4)} { 
			     set avoidableDash {2 2}
			 }
			 if {($type==3)||($type==4)} { set ineluctable [list  [expr {11*$zoom}] [expr {6*$zoom}] [expr {6*$zoom}]] }
		       }
		   } 

                    if {$nbTokenColor($tpn(courant))>1 } {set  epaisseur 2}
                    set epaisseur [format "%.1f" [expr {max(1,$epaisseur*$zoom*$::eparcs)}]] 


    
		    if {$arrow==0} {
			   set leMotifFleche [$c create line $xa $ya $xArrow $yArrow  -dash $avoidableDash -width $epaisseur -tags item -fill $laCouleur]
		    } elseif {$arrow==1} {
			   set leMotifFleche [$c create line $xa $ya $xb $yb  -dash $avoidableDash -width $epaisseur -arrowshape $flecheNormal -arrow last -tags item -fill $laCouleur]
		    } elseif {$arrow==-1} {
			set leMotifFleche [$c create line $xa $ya $xb $yb  -dash $unctrlDash -width $epaisseur -arrowshape $ineluctable -arrow first -tags item -fill $laCouleur]
		    }
            return $leMotifFleche
}		    


proc faireUnArcPnT {c xa ya xb yb xc yc laCouleur arrow type offset} {
    global dimension
    global xArrow
    global yArrow
    global controle
    global nbTokenColor tpn zoom


           set r $dimension(place)
           set l $dimension(largeurTransition)
           set h $dimension(hauteurTransition)
           set fl $dimension(flush)


		    set offsetX 0
		    set offsetY 0
		    # il faut maintenant retirer  a/sqrt(a*a+b*b) pour partir du bord du cercle :
		    # le rayon du cercle est $r (8 pour zoom = 1)
		    set hypo [expr hypot($xb-$xa, [expr $yb-$ya])]
		    if {$hypo==0} {set hypo 1}
		    set rx [expr ($xa-$xb)*8/$hypo]
		    set ry [expr ($ya-$yb)*8/$hypo]
		    set xa [expr $xa-$rx]
		    set ya [expr $ya-$ry]
		    # pour partir du bord de la transition
		    set den [expr $xc-$xb]
		    set deltX -1
		    set deltY -1
		    if {$den==0} {set den 1}
		    if {[expr abs(($yc-$yb)/($den))]<0.3} {
		      set offsetY $offset
			  if {$yc>$yb} { set deltY -1} else { set deltY 1}
			  if {$xc>$xb} { 
			    set xc [expr $xc-$l] 
			    set deltX -1
			  } else { 
			    set xc [expr $xc+$l] 
			    set deltX 1
			  }
		    } else {
		      set offsetX $offset
			  if {$xc>$xb} { set deltX -2} else { set deltX 2}
			  if {$yc>$yb} { 
			    set yc [expr $yc-$h] 
			    set deltY -1
			  } else { 
			    set yc [expr $yc+$h] 
			    set deltY 1
			  }
		    }

		    # courbe de Bezier passant par B (approx) [expr (2*$xb-($xa+$xc)/2)] [expr (2*$yb-($ya+$yc)/2)]


                   set avoidableDash {}
                   set unctrlDash {}
                   set epaisseur 1
                   set flecheNormal [list  [expr {7*$zoom}] [expr {12*$zoom}] [expr {4*$zoom}]]
                   set ineluctable $flecheNormal
                   if {($controle > 1)&&($type>0)} {
      		         set epaisseur 2
		         set unctrlDash {4 2}
		         set avoidableDash {2 4}
                   } elseif {$controle == 1} {
                     if {$type>0} {
		         set  epaisseur 1
		         set unctrlDash {6 4}
			 if {($type==2)||($type==4)} { 
			     set avoidableDash {2 2}
			 }
			 if {($type==3)||($type==4)} { set ineluctable [list  [expr {11*$zoom}] [expr {6*$zoom}] [expr {6*$zoom}]] }
		     }
		    }

                    if {$nbTokenColor($tpn(courant))>1 } {set  epaisseur 2}
    
    set epaisseur [format "%.1f" [expr {max(1,$epaisseur*$zoom*$::eparcs)}]] 

    
		    if {$arrow==0} {
		       set xArrow [expr $xc + $fl*$deltX + $offsetX*$deltX] 
			   set yArrow [expr $yc + $fl*$deltY + $offsetY*$deltY] 
 			   set leMotifFleche [$c create line $xa $ya [expr (2*$xb-($xa+$xArrow)/2)] [expr (2*$yb-($ya+$yArrow)/2)] $xArrow $yArrow  -dash $avoidableDash -width $epaisseur -smooth 1 -tags item -fill $laCouleur]
		    } elseif {$arrow==1} {

 			   set leMotifFleche [$c create line $xa $ya [expr (2*$xb-($xa+$xc)/2)] [expr (2*$yb-($ya+$yc)/2)] $xc $yc   -dash $avoidableDash -arrowshape $flecheNormal -width $epaisseur  -smooth 1 -arrow last -tags item -fill $laCouleur]
		     } else  {
 			   set leMotifFleche [$c create line $xa $ya [expr (2*$xb-($xa+$xc)/2)] [expr (2*$yb-($ya+$yc)/2)] $xc $yc  -dash $unctrlDash -width $epaisseur -arrowshape $ineluctable  -smooth 1 -arrow first -tags item -fill $laCouleur]
		     } 
            return $leMotifFleche

}		    


