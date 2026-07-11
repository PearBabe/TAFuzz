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

proc isSynchronized {numTransition} {
global synchronized
    set resul 0
    for {set i 0} {$i<[llength $synchronized]} {incr i} {
	if {[lsearch [lindex $synchronized $i] $numTransition] > -1} {
	   set resul 1
       }
    }
return $resul

}

proc deleteTransInSynch {numTransition} {
global synchronized
    for {set i 0} {$i<[llength $synchronized]} {incr i} {
	if {[lsearch [lindex $synchronized $i] $numTransition] > -1} {
	    set laListe [lreplace [lindex $synchronized $i] [lsearch [lindex $synchronized $i] $numTransition]  [lsearch [lindex $synchronized $i] $numTransition] ]
	    if {[llength $laListe]>1} {
		set synchronized [lreplace $synchronized $i [expr $i+1] $laListe]
	    } else {
		#supprimer synchro a un seul element ??????
		set synchronized [lreplace $synchronized $i $i]
		set i [expr $i-1]
	    }
       }
    }
}


proc isInFuncSynch {listeSynch numTransition} {
    set resul -1
    for {set i 0} {$i<[llength $listeSynch]} {incr i} {
	if {[lsearch [lindex $listeSynch $i] $numTransition] > -1} {
	   set resul $i
       }
    }
return $resul
}

proc fonctionSynchro {listeSynch numTransition} {

    set resul [list]
    for {set i 0} {$i<[llength $listeSynch]} {incr i} {
	if {[lsearch [lindex $listeSynch $i] $numTransition] > -1} {
	    lappend resul [lindex $listeSynch $i]
	}
    }
return $resul
}

proc defineSynchro {forg numTransition} {
global tabTransition 
    global tpn tabUnDo
 
global synchronized
global listeSynchLocal
global tabSynchLocal
global fin ok

    set fs .synchronizationVectors
    catch {destroy $fs}
    toplevel $fs

    frame $fs.listeSynchro  -relief ridge -bd 4
    label $fs.listeSynchro.titre
    pack $fs.listeSynchro.titre -side top
    $fs.listeSynchro.titre config -text "A transition involved in a synchronization vector \n must be fired within one list of transitions \n \n Synchronisation vectors :"

# indide -1 pour avoir un vecteur libre
    for {set i -1} {$i<[llength $synchronized]} {incr i} {
    set newline 1
      for {set j 1} {$tabTransition($tpn(courant),$j,statut)!=$fin} {incr j} {
	if {$tabTransition($tpn(courant),$j,statut)==$ok} {
	    if {[lsearch [lindex $synchronized $i] $j]> -1} {
		set tabSynchLocal($i,$j) 1
	    } else {
		set tabSynchLocal($i,$j) 0
	    }
	    if {$newline} {
	      frame $fs.listeSynchro.$i
              pack  $fs.listeSynchro.$i -side top
	      set newline 0
            }
	    checkbutton $fs.listeSynchro.$i.$j -text $j  -variable tabSynchLocal($i,$j) \
	   -relief flat -anchor w -selectcolor red -command "verifierSynch $i $j"
           pack $fs.listeSynchro.$i.$j -side left -pady 2 -anchor w
        }
      }
    }
    pack $fs.listeSynchro -side left 
    frame $fs.indice  -relief ridge -bd 4
    afficheIndiceTransition $fs.indice
    pack $fs.indice -side right

    bind $fs <Return> "validerSynch $forg $fs $numTransition"
    bind $fs <Escape> "destroy $fs"
    frame $fs.buttons
    pack $fs.buttons -side bottom -fill x -pady 2m
    button $fs.buttons.annuler -text Cancel -command  "destroy $fs"
#    button $fs.buttons.test -text test -command  "deleteTransInSynch $numTransition"
    button $fs.buttons.accepter -default active -text "  Ok  " \
		-command "validerSynch $forg $fs $numTransition"
    pack $fs.buttons.accepter $fs.buttons.annuler  -side left -expand 1
#    pack $fs.buttons.test
}

proc validerSynch {f1 f2 numTransition} {
 global tabTransition 
    global tpn tabUnDo
 global tabSynchLocal
 global listeSynchLocal
 global synchronized
 global ok fin

    set listeSynchLocal [list]
    for {set i -1} {$i<[llength $synchronized]} {incr i} {
    set uneFonction [list]
     for {set j 1} {$tabTransition($tpn(courant),$j,statut)!=$fin} {incr j} {
	if {$tabTransition($tpn(courant),$j,statut)==$ok} {
	    if {$tabSynchLocal($i,$j)==1} {
		lappend uneFonction $j
	    }
	}
     }
	if {[llength $uneFonction]>1} {lappend listeSynchLocal $uneFonction}
    }

    

    # destroy $f1.synchro.etat
    if {[isInFuncSynch $listeSynchLocal $numTransition]>-1} {
	$f1.synchro.etat config -text [fonctionSynchro  $listeSynchLocal $numTransition]
	} else {
	     $f1.synchro.etat config -text "no synchronization"
	}    

set synchronized  $listeSynchLocal
destroy $f2
}

proc verifierSynch {nL nT} {
 global tabTransition 
    global tpn tabUnDo 
 global tabSynchLocal
 global infini
 global parameters

 if {$parameters==0} {	
    if {!(($tabTransition($tpn(courant),$nT,dmin)==0)&&(($tabTransition($tpn(courant),$nT,dmax)==0)||($tabTransition($tpn(courant),$nT,dmax)==$infini)))} {
	if {$tabTransition($tpn(courant),$nT,dmax)==$infini} { set bomax "infty\["} else {set bomax $tabTransition($tpn(courant),$nT,dmax)\]}
        set button [tk_messageBox -icon error -message  "Only \[0,0\] or \[0,infty\[ transition is allowed in synchronization function. \n Here :\[$tabTransition($tpn(courant),$nT,dmin),$bomax"] 
        set tabSynchLocal($nL,$nT) 0
    }
 } else {
     if {!(((![string compare $tabTransition($tpn(courant),$nT,minparam) "0"])||(![string compare $tabTransition($tpn(courant),$nT,minparam) ""]))&&((![string compare $tabTransition($tpn(courant),$nT,maxparam) ""])||(![string compare $tabTransition($tpn(courant),$nT,maxparam) "0"])||(![string compare $tabTransition($tpn(courant),$nT,maxparam) "$infini"])))} {
	if {$tabTransition($tpn(courant),$nT,maxparam)==""} { set bomax "infty\["} else {set bomax $tabTransition($tpn(courant),$nT,maxparam)\]}
        set button [tk_messageBox -icon error -message  "Only \[0,0\] or \[0,infty\[ transition is allowed in synchronization function. \n Here :\[$tabTransition($tpn(courant),$nT,minparam),$bomax"] 
        set tabSynchLocal($nL,$nT) 0
    }
 }}
proc afficheIndiceTransition {fs} {
    global tabTransition 
    global tpn tabUnDo
    global tpn tabUnDo 
    global fin
    global ok
    global infini

    text $fs.text -yscrollcommand "$fs.vscroll set" -setgrid true \
	-width 20 -height 8
    scrollbar $fs.vscroll -command "$fs.text yview"
    # -xscrollcommand "$fi.hscroll set"
    # scrollbar $fi.hscroll -orient horiz -command "$fi.text xview"


    pack $fs.vscroll -side right -fill y
    pack $fs.text -expand yes -fill both
    # pack $fi.hscroll -side bottom -fill x

    $fs.text tag configure rouge -foreground red
    $fs.text tag configure surgris -background #a0b7ce
    $fs.text tag configure souligne -underline on


    $fs.text insert end "  Transition             \n" souligne
    $fs.text insert end "Index " surgris
    $fs.text insert end "  \"label\" \n" rouge


    # place par place
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin} {incr i} {
	if {$tabTransition($tpn(courant),$i,statut)==$ok} {
	    $fs.text insert end "$i     " surgris
	    $fs.text insert end "  \"$tabTransition($tpn(courant),$i,label,nom)\"\n" rouge
	}
    }
}
