# This file is part of the Rom√©o model-checking software
# 
# Copyright University of Nantes, √âcole Centrale de Nantes, IRCCyN
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


# procedure associe au menu Parametric-PN : additionalConstraints




#******** ajout de contraintes supplementaires sur les parametres***************

proc additionalConstraints {} {
    global tabConstraint typePN
    global tpn tabUnDo
    global nbConstraints
    global cons
    global nbCons
    global nbSaisie
    global modif
    
    set f .fenetreConstraint
    catch {destroy $f}
    toplevel $f
    wm title $f [mc "Additional constraints"]

    frame $f.description
    label $f.description.titre
    pack $f.description.titre -side top
    $f.description.titre config -text [mc "Add linear constraints on the parameters:"] -font menufont
    pack $f.description -side top -fill x

    for {set i 0} {$i<$nbConstraints($tpn(courant))} {incr i} { 
	set cons($i) $tabConstraint($tpn(courant),$i)
    }
    set nbCons $nbConstraints($tpn(courant))

    button $f.and -text [mc "and"] -font menufont -command  "addConstraint $f"
    pack $f.and -side right

    for {set i 0} {$i<$nbConstraints($tpn(courant))} {incr i} {
	frame $f.saisieConstraints($i) -bd 2
	entry $f.saisieConstraints($i).addConstraint -justify left  -textvariable cons($i) -font menufont -relief sunken -width 20 -bg white
  	button $f.saisieConstraints($i).bclear -text [mc "clear"] -font menufont -command  "clearConstraint $i $f"
    	pack $f.saisieConstraints($i).bclear -side right
	pack $f.saisieConstraints($i).addConstraint -side left
	pack $f.saisieConstraints($i) -side top -fill x
    }
    set nbSaisie $nbConstraints($tpn(courant))

    bind $f <Return> "validerCons $f"

    frame $f.buttons
    pack $f.buttons -side bottom -fill x -pady 2m
    button $f.buttons.annuler -text [mc "Cancel"] -font menufont -command  "destroy $f"
    button $f.buttons.accepter -default active -text [mc "Ok"] -font menufont  -command "validerCons $f"
    pack $f.buttons.annuler $f.buttons.accepter  -side left -expand 1

    # ++++++ procedures internes ‡ la procedure additionalConstraints

    proc validerCons {fl} {
        global tabConstraint
	global cons
	global modif 
	global tpn tabUnDo
	global nbConstraints
	global nbCons

	modifTPN $tpn(courant)
        set lesErreurs ""
	set j 0

    	for {set i 0} {$i<$nbCons} {incr i} {
		if {[string length $cons($i)] > 0 } {
		    set erreur [verifSyntaxeContrainte $cons($i)]
                    if {$erreur==""} {
 	                set tabConstraint($tpn(courant),$j) $cons($i)
                    } else { 
			set lesErreurs  "$lesErreurs\Error in constraint: $cons($i) \n      $erreur \n"
			set tabConstraint($tpn(courant),$j) ""
                    }
		    incr j
		}
	}


	if { $j > 0} {
	     set nbConstraints($tpn(courant)) $j
	} else {
	     set nbConstraints($tpn(courant)) 1
             set tabConstraint($tpn(courant),0) ""
        } 

    if {$lesErreurs!= ""} {
         set button [tk_messageBox -icon error -message  "$lesErreurs"]
    } else {
	destroy $fl
    }
  }

    proc addConstraint {fl} {
	global cons
	global nbCons
        global nbSaisie

	set cons($nbCons) ""	

	frame $fl.saisieConstraints($nbCons) -bd 2
	entry $fl.saisieConstraints($nbCons).addConstraint -justify left -textvariable cons($nbCons) -relief sunken -width 20 -bg white
	pack $fl.saisieConstraints($nbCons).addConstraint -side left
  	button $fl.saisieConstraints($nbCons).bclear -text [mc "clear"] -command  "clearConstraint $nbCons $fl"
    	pack $fl.saisieConstraints($nbCons).bclear -side right
	pack $fl.saisieConstraints($nbCons) -side top -fill x

	incr nbCons
	incr nbSaisie
    }

    proc clearConstraint {li fl} {
	global cons
	global nbCons
        global nbSaisie

	set cons($li) "" 

	if {$nbSaisie > 1} {
		place forget $fl.saisieConstraints($li) 
		set nbSaisie [expr $nbSaisie-1]
	}
    }

    # fin de la procedure additionalConstraints
}


#--------------Quand on ouvre un RdP dans un mode qui n'est pas celui dans lequel il a ÈtÈ cree (parametre ou non)

proc heritageOuPas {lePetri} {
global tabTransition 
global tpn tabUnDo
global fin ok infini

  set paramVide 1
  set tempoVide 1

    for {set i 1} {$tabTransition($lePetri,$i,statut)!=$fin}  {incr i} {
	if {$tabTransition($lePetri,$i,statut) == $ok} {
		if {($tabTransition($lePetri,$i,minparam)!= "")||($tabTransition($tpn(courant),$i,maxparam)!= "")} {
  		       set paramVide 0
		}
		if {($tabTransition($lePetri,$i,dmin)!= 0)||($tabTransition($tpn(courant),$i,dmax)!= $infini)} {
		       set tempoVide 0
		}
	}
    }
  if {($paramVide)&&($tempoVide==0)} {
      heriterContrainteTempo 2 $lePetri
  } elseif {$tempoVide} {
      heriterContrainteTempo 0 $lePetri
  }
}

#--------------Quand on bascule  vers le mode parametre 
proc  heriterContrainteTempo2 {parametre lePetri} {
global tabTransition 
global tpn tabUnDo
global fin ok infini

  set paramVide 1
  set tempoVide 1

     for {set i 1} {$tabTransition($lePetri,$i,statut)!=$fin}  {incr i} {
	if {$tabTransition($lePetri,$i,statut) == $ok} {
		if {($tabTransition($lePetri,$i,minparam)!= "")||($tabTransition($tpn(courant),$i,maxparam)!= "")} {
  		       set paramVide 0
		}
		if {($tabTransition($lePetri,$i,dmin)!= 0)||(($tabTransition($tpn(courant),$i,dmax)!= $infini)&&($tabTransition($tpn(courant),$i,dmax)!= 0))} {
		       set tempoVide 0
		}
	}
    }
    if {(($paramVide)&&($parametre>=1))||(($tempoVide)&&($parametre<1))} {
      heriterContrainteTemporel $parametre $lePetri
    }
}


#--------------Quand on bascule  vers le mode parametre 

proc heriterContrainteTempo {parametre lePetri} {
global tabTransition 
global tpn tabUnDo
global fin ok infini
global modif

    
  if {$parametre>=1} {
    for {set i 1} {$tabTransition($lePetri,$i,statut)!=$fin}  {incr i} {
	if {$tabTransition($lePetri,$i,statut) == $ok} {
		if {[entier [sansEspace $tabTransition($lePetri,$i,minparam)]]||($tabTransition($lePetri,$i,minparam)== "")} {
		    if {($tabTransition($lePetri,$i,dmin)== 0)} {
			set tabTransition($lePetri,$i,minparam) ""
		    } else {
			set tabTransition($lePetri,$i,minparam) $tabTransition($lePetri,$i,dmin)
		    }
#		    modifTPN $lePetri
                }
	        if {[entier [sansEspace $tabTransition($lePetri,$i,maxparam)]]||($tabTransition($lePetri,$i,maxparam)== "")} {
		    if {($tabTransition($lePetri,$i,dmax)== $infini)} {
			set tabTransition($lePetri,$i,maxparam) ""
		    } else {
		        set tabTransition($lePetri,$i,maxparam) $tabTransition($lePetri,$i,dmax)
                    }
#		    set modif($lePetri) 1
		}
	}
    }
  } else {
    for {set i 1} {$tabTransition($lePetri,$i,statut)!=$fin}  {incr i} {
	if {$tabTransition($lePetri,$i,statut) == $ok} {
		if {($tabTransition($lePetri,$i,minparam)!= "")} {
		    if {[entier [sansEspace $tabTransition($lePetri,$i,minparam)]]} {
			set tabTransition($lePetri,$i,dmin)  [sansEspace $tabTransition($lePetri,$i,minparam)]
#			set modif($lePetri) 1
			if {(![entier [sansEspace $tabTransition($lePetri,$i,maxparam)]])&&($tabTransition($lePetri,$i,dmin) > $tabTransition($lePetri,$i,dmax))} {
			   set tabTransition($lePetri,$i,dmax) $tabTransition($lePetri,$i,dmin)
			}
		    }
                } else {
		     if {($tabTransition($lePetri,$i,dmin) != 0)} {
			 set tabTransition($lePetri,$i,dmin) 0
#			 set modif($lePetri) 1
		     }
		}
		if {($tabTransition($lePetri,$i,maxparam)!= "")} {
		    if {[entier [sansEspace $tabTransition($lePetri,$i,maxparam)]]} {
			set tabTransition($lePetri,$i,dmax) [sansEspace $tabTransition($lePetri,$i,maxparam)]
#		        set modif($lePetri) 1
			if {(![entier [sansEspace $tabTransition($lePetri,$i,minparam)]])&&($tabTransition($lePetri,$i,dmin) > $tabTransition($lePetri,$i,dmax))} {
			   set tabTransition($lePetri,$i,dmin) $tabTransition($lePetri,$i,dmax)
			}
		    }
		} else {
		     if {($tabTransition($lePetri,$i,dmax)!= $infini)} {
			 set tabTransition($lePetri,$i,dmax) $infini
#			 set modif($lePetri) 1
		     }
		}
		if {$tabTransition($lePetri,$i,dmin) > $tabTransition($lePetri,$i,dmax)} {
                    set tabTransition($lePetri,$i,dmin)  $tabTransition($lePetri,$i,dmax)
		}	      				       
	}
    }
  }
}


#-------

proc addingTimedCost {} {
    global tpn tabUnDo timedCost letimedcost
    global modif
    
    set f .fenetreCost
    catch {destroy $f}
    toplevel $f
    wm title $f [mc "Timed cost"]

    set letimedcost $timedCost($tpn(courant)) 

    frame $f.description
    label $f.description.titre
    pack $f.description.titre -side top
    $f.description.titre config -text [mc "Add linear timed cost to the TPN:"] -font menufont
    pack $f.description -side top -fill x


    frame $f.cost -relief ridge -bd 2
    pack $f.cost -side top
    label $f.cost.label
    pack  $f.cost.label -side left
    $f.cost.label config -text "Cost:  "  -font menufont


   entry $f.cost.saisiecost -justify left -textvariable letimedcost -relief sunken -width 80 -bg white
	pack $f.cost.saisiecost -side left


    bind $f <Return> "validerCost $f"

    frame $f.buttons
    pack $f.buttons -side bottom -fill x -pady 2m
    button $f.buttons.annuler -text [mc "Cancel"] -font menufont -command  "destroy $f"
    button $f.buttons.accepter -default active -text [mc "Ok"] -font menufont  -command "validerCost $f"
    pack $f.buttons.annuler $f.buttons.accepter  -side left -expand 1


    proc validerCost {fl} {
    global tpn tabUnDo timedCost letimedcost


	modifTPN $tpn(courant)

	set timedCost($tpn(courant)) $letimedcost



# TODO HERE
	destroy $fl
  }

}
