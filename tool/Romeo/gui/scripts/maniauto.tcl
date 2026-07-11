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


#********
#*********
#************************generer l'automate UPPAAL ***************************

proc genererAutomateUPPAAL {fichier} {
    global tabPlace
    global tabTransition
    global tpn tabUnDo
    global nbProcesseur
    global fin
    global ok destroy
    global infini


    if [string compare $fichier ""] {
        set File [open $fichier w]
        affiche "\n"
        affiche [format [mc "-Translating TPN to TA (UPPAAL format) in %s ..."] $fichier]
	
        set timeBegin [clock clicks -milliseconds]
	
	
	# determinons le nombre de place :
	set nbPlace 0
	for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
	    if {$tabPlace($tpn(courant),$i,statut)==$ok} {incr nbPlace} }

	# determinons le nombre de transition :
	set nbTrans 0
	for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
	    if {$tabTransition($tpn(courant),$i,statut)==$ok} {incr nbTrans} }

	# puts $File  "chan  pre, post, update ; \n int n, i ; \n int\[0,1\] M\[$nbPlace\] ; \n\
	    
	
	
	set ligne "\{";
	set numeroPlace 0
	for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
	    if {$tabPlace($tpn(courant),$i,statut)==$ok} {
		set ligne "$ligne$tabPlace($tpn(courant),$i,jeton)"
		set j 1
		while {($tabPlace($tpn(courant),[expr $i+$j],statut)==$destroy)} {incr j}
		if {$tabPlace($tpn(courant),[expr $i+$j],statut)==$ok} {set ligne "$ligne, "}
		set numeroPlace [expr $numeroPlace + 1]
	    }
      	}

	puts $File  "chan  pre, post; \n broadcast chan update ; \n int\[0,15\] M\[$nbPlace\]:=$ligne\} ; \n\
		process supervisor\{ \n \
		state S0, S1, S2, S3; \n \
		commit S1, S2, S3; \n \
		init S3; \n \
		trans S0 -> S1 \{sync pre?; \} , \n \
		S1 -> S2 \{sync update!; \} , \n \
		S2 -> S3 \{sync post?; \} , \n \
		S3 -> S0 \{sync update!; \} ; \n\} \n"

	# determinons tous les types de transition du reseau
	# on commence par maxB : maximum des places amont
	set maxB 0
	for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
	    if {$tabTransition($tpn(courant),$i,statut)==$ok} {
		for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} {}
		if {$maxB<$j-1} {set maxB [expr $j - 1]} } }

	# on commence par maxF : maximum des places aval
	set maxF 0
	for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
	    if {$tabTransition($tpn(courant),$i,statut)==$ok} {
		for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} {}
		if {$maxF<$j-1} {set maxF [expr $j - 1]} } }

	# puts $File "  maxB = $maxB  et maxF = $maxF"

	for {set i 0} {$i <=$maxB} {incr i} {
	    for {set j 0} {$j <=$maxF} {incr j} {
		if { [existeTrans $i $j]==1} {
		    set ligne "process  [sansEspace "T $i b $j f \(" ] const"
		    for {set bfi 1} {$bfi <= $i} {incr bfi} {set ligne "$ligne B$bfi , weightB$bfi , "}
		    for {set bfi 1} {$bfi <= $j} {incr bfi} {set ligne "$ligne F$bfi , weightF$bfi , "}
		    puts $File "$ligne dmin , dmax \) \{ \n \
			clock x; \n \
			state notenable, enable\{x<=dmax\}, firing; \n \
			init notenable; "
		    
		    set ligne "true"
		    for {set bfi 1} {$bfi <= $i} {incr bfi} {set ligne "$ligne , M\[B$bfi\]>=weightB$bfi"}
		    puts $File "  trans notenable -> enable \{guard $ligne ; sync update?; assign x:=0; \}, \n       \
			enable -> enable \{guard $ligne ; sync update?; \}, "

		    set ligne ""
		    for {set bfi 1} {$bfi <= $i} {incr bfi} {
			puts $File "        enable -> notenable \{guard M\[B$bfi\]<weightB$bfi; sync update?; \}, "
			puts $File "        notenable -> notenable \{guard M\[B$bfi\]<weightB$bfi; sync update?; \}, "
			if {$bfi==1} {set ligne "assign"}
			set ligne "$ligne M\[B$bfi\]:=M\[B$bfi\]-weightB$bfi"
			if {$bfi==$i} {set ligne "$ligne ;"} else {set ligne "$ligne ,"} 
		    }
		    puts $File "        enable -> firing \{guard x>=dmin, x<=dmax; sync pre!; $ligne \}, "

		    set ligne ""
		    for {set bfi 1} {$bfi <= $j} {incr bfi} {
			if {$bfi==1} {set ligne "assign"}
			set ligne "$ligne M\[F$bfi\]:=M\[F$bfi\]+weightF$bfi "
			if {$bfi==$j} {set ligne "$ligne ;"} else {set ligne "$ligne ,"} 
		    }

		    puts $File "        firing -> notenable \{sync post! ; $ligne \}, \n       \
			firing -> firing \{sync update?; \} ; \n\}"
		}

		if { [existeTransInfty $i $j]==1} {
		    set ligne "process  [sansEspace "T $i b $j f Infty \(" ] const"
		    for {set bfi 1} {$bfi <= $i} {incr bfi} {set ligne "$ligne B$bfi , weightB$bfi , "}
		    for {set bfi 1} {$bfi <= $j} {incr bfi} {set ligne "$ligne F$bfi , weightF$bfi , "}
		    puts $File "$ligne dmin \) \{ \n \
			clock x; \n \
			state notenable, enable, firing; \n \
			init notenable; "
		    
		    set ligne "true"
		    for {set bfi 1} {$bfi <= $i} {incr bfi} {set ligne "$ligne , M\[B$bfi\]>=weightB$bfi"}
		    puts $File "  trans notenable -> enable \{guard $ligne ; sync update?; assign x:=0; \}, \n       \
			enable -> enable \{guard $ligne ; sync update?; \}, "

		    set ligne ""
		    for {set bfi 1} {$bfi <= $i} {incr bfi} {
			puts $File "        enable -> notenable \{guard M\[B$bfi\]<weightB$bfi; sync update?; \}, "
			puts $File "        notenable -> notenable \{guard M\[B$bfi\]<weightB$bfi; sync update?; \}, "
			if {$bfi==1} {set ligne "assign"}
			set ligne "$ligne M\[B$bfi\]:=M\[B$bfi\]-weightB$bfi"
			if {$bfi==$i} {set ligne "$ligne ;"} else {set ligne "$ligne ,"} 
		    }
		    puts $File "        enable -> firing \{guard x>=dmin; sync pre!; $ligne \}, "

		    set ligne ""
		    for {set bfi 1} {$bfi <= $j} {incr bfi} {
			if {$bfi==1} {set ligne "assign"}
			set ligne "$ligne M\[F$bfi\]:=M\[F$bfi\]+weightF$bfi "
			if {$bfi==$j} {set ligne "$ligne ;"} else {set ligne "$ligne ,"} 
		    }

		    puts $File "        firing -> notenable \{sync post! ; $ligne \}, \n       \
			firing -> firing \{sync update?; \} ; \n\}"
		}
	    }
	}   

	set declareSystem "system"
	set numTrans 0
	for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
	    if {$tabTransition($tpn(courant),$i,statut)==$ok} {
		for {set nborg 0} {$tabTransition($tpn(courant),$i,Porg,[expr $nborg + 1]) >0}   {incr nborg} {}
		for {set nbdes 0} {$tabTransition($tpn(courant),$i,Pdes,[expr $nbdes + 1]) >0}   {incr nbdes} {}

		set nomTransition [sansEspace $tabTransition($tpn(courant),$i,id)]
		set declareSystem "$declareSystem Tr$numTrans\_$nomTransition," 
		
		if {$tabTransition($tpn(courant),$i,dmax)!=$infini} {
		    set ligne "Tr$numTrans\_$nomTransition  := [sansEspace "T $nborg b $nbdes f "] ("
		    set maxd ", $tabTransition($tpn(courant),$i,dmax)"
		} else {
		    set ligne "Tr$numTrans\_$nomTransition := [sansEspace "T $nborg b $nbdes f Infty"] ("
		    set maxd ""
		} 
		
		for {set j 1} {$tabTransition($tpn(courant),$i,Porg,$j) >0}   {incr j} {
		    set ligne "$ligne [iPU $tabTransition($tpn(courant),$i,Porg,$j)], $tabTransition($tpn(courant),$i,PorgWeight,$j),"}

		for {set j 1} {$tabTransition($tpn(courant),$i,Pdes,$j) >0}   {incr j} {
		    set ligne "$ligne [iPU $tabTransition($tpn(courant),$i,Pdes,$j)], $tabTransition($tpn(courant),$i,PdesWeight,$j),"}
		puts $File "$ligne $tabTransition($tpn(courant),$i,dmin) $maxd);" 
		incr numTrans
	    }
	}

	puts $File "SU := supervisor (); \n$declareSystem SU;"

	set timeEnd [clock clicks -milliseconds]

	close $File
	affiche " done in [expr $timeEnd - $timeBegin] ms "
    }
} 


# indicePlaceUppaal attention cette procedure est aussi utilis�e par toutcommeyfaut

proc iPU {indiceP} {
    global tabPlace
    global tpn tabUnDo
    global ok

    set numeroPlace 0
    for {set i 1} {$i<$indiceP} {incr i} {
	if {$tabPlace($tpn(courant),$i,statut)==$ok} {
	    set numeroPlace [expr $numeroPlace + 1]
	}
    }
    return $numeroPlace
} 

proc genererAutomateUPPAALSous {} {
    global nomRdP
    global tpn tabUnDo

    if {[verifSem 1]==1} {

        set last [string first ".xml" $nomRdP($tpn(onglet))]
        if {$last>=0} {
            set nomCompil [string range $nomRdP($tpn(onglet)) 0 [expr $last -1]]
        } else { 
            set nomCompil $nomRdP($tpn(onglet))
        }  
        

        #   Type names      Extension(s)    Mac File Type(s)
        #
        #---------------------------------------------------------
        set types {{"fichier UPPAAL"     {.xta}       TEXT}}
        set fichier [tk_getSaveFile -filetypes $types -initialdir [repertoire $nomRdP($tpn(onglet))] \
			 -initialfile [nomSeul $nomCompil\-struct.xta] -defaultextension .xta -title [mc "Structural translation to Timed Automaton:"]]
	
        set fichier [sansEspace $fichier]
        if [string compare $fichier ""] { 
            genererAutomateUPPAAL $fichier 
        }
    }

}


#********
#********

proc  existeTrans {nbPre nbPost} {
    global tabTransition 
    global tpn tabUnDo
    global fin
    global ok
    global infini

    for {set a 1} {$tabTransition($tpn(courant),$a,statut)!=$fin}  {incr a} {
	if {$tabTransition($tpn(courant),$a,statut)==$ok} {
	    if {$tabTransition($tpn(courant),$a,dmax)!=$infini} {
		for {set b 1} {$tabTransition($tpn(courant),$a,Porg,$b) >0}  {incr b} {}
		if {$b==$nbPre+1} {
		    for {set c 1} {$tabTransition($tpn(courant),$a,Pdes,$c) >0}  {incr c} {}
		    if {$c==$nbPost+1} {return 1}  
		}
	    }  
	}
    }
    return 0
}

proc  existeTransInfty {nbPre nbPost} {
    global tabTransition 
    global tpn tabUnDo
    global fin
    global ok
    global infini

    for {set a 1} {$tabTransition($tpn(courant),$a,statut)!=$fin}  {incr a} {
	if {$tabTransition($tpn(courant),$a,statut)==$ok} {
	    if {$tabTransition($tpn(courant),$a,dmax)==$infini} {
		for {set b 1} {$tabTransition($tpn(courant),$a,Porg,$b) >0}  {incr b} {}
		if {$b==$nbPre+1} {
		    for {set c 1} {$tabTransition($tpn(courant),$a,Pdes,$c) >0}  {incr c} {}
		    if {$c==$nbPost+1} {return 1}  
		}
	    }  
	}
    }
    return 0
}


proc afficheCorresUPPAAL {} {
    global tabTransition 
    global tpn tabUnDo
    global tabPlace
    global fin
    global ok
    global infini


    set corresUPPAAL .fenetreCorresUPPAAL
    catch {destroy $corresUPPAAL }
    toplevel $corresUPPAAL

    wm title $corresUPPAAL [mc "Net labels -> UPPAAL index"]
    text $corresUPPAAL.text -yscrollcommand "$corresUPPAAL.scroll set" -setgrid true \
	-width 60 -height 12 -wrap word
    scrollbar $corresUPPAAL.scroll -command "$corresUPPAAL.text yview"

    pack $corresUPPAAL.scroll -side right -fill y
    pack $corresUPPAAL.text -expand yes -fill both

    $corresUPPAAL.text tag configure rouge -foreground red
    $corresUPPAAL.text tag configure surgris -background #a0b7ce
    $corresUPPAAL.text tag configure souligne -underline on

    $corresUPPAAL.text insert end "                                             \n" souligne
    $corresUPPAAL.text insert end " TRANSITION                                  \n" souligne
    $corresUPPAAL.text insert end "UPPAAL" surgris
    $corresUPPAAL.text insert end "    \" label \"    " rouge
    $corresUPPAAL.text insert end " \[ dmin , dmax \] \n\n"


    # transition par transition
    set indice 0
    for {set i 1} {$tabTransition($tpn(courant),$i,statut)!=$fin}  {incr i} {
	if {$tabTransition($tpn(courant),$i,statut)==$ok} {
	    $corresUPPAAL.text insert end "   $indice   " surgris
	    $corresUPPAAL.text insert end "              \" $tabTransition($tpn(courant),$i,id) \"    " rouge
	    if {$tabTransition($tpn(courant),$i,dmax) < $infini} {
		$corresUPPAAL.text insert end "   \[ $tabTransition($tpn(courant),$i,dmin) , $tabTransition($tpn(courant),$i,dmax)\] \n"
	    } else {
		$corresUPPAAL.text insert end "   \[ $tabTransition($tpn(courant),$i,dmin) , infini \[ \n"
	    }
	    incr indice
	}
    }

    $corresUPPAAL.text insert end "\n                                             \n" souligne
    $corresUPPAAL.text insert end "  PLACE                                      \n" souligne
    $corresUPPAAL.text insert end "UPPAAL " surgris
    $corresUPPAAL.text insert end "    \" label \"    " rouge
    $corresUPPAAL.text insert end "    M0 \n \n"


    # place par place
    set indice 0
    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
	if {$tabPlace($tpn(courant),$i,statut)==$ok} {
	    $corresUPPAAL.text insert end "   $indice   " surgris
	    $corresUPPAAL.text insert end "          \" $tabPlace($tpn(courant),$i,id) \"    " rouge
	    $corresUPPAAL.text insert end "    $tabPlace($tpn(courant),$i,jeton) \n"
	    incr indice
	}
    }

    #++++++++++++++++++




    # label $corresUPPAAL.msg -wraplength 4i -justify left -text "$texte"
    # pack $corresUPPAAL.msg -side top
}
