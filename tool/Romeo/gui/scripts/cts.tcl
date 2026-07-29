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

# Rappel  TypeArc 0 = PlaceTransition  ---  1 = flush --- 2 = read --- 3 = logicalInhibitor, ------ otherwise 4 = timedInhibitor




#+++++++++++++++++++++ GENERER FICHIER XML +++++++++++++++++++++++++++ 
proc exportversCTS {formule avecAffichage} { 
    global tabPlace tabTransition tabConstraint 
    global nbProcesseur  
    global fin ok 
    global modif nomRdP
    global infini 
    global tabColor 
    global nbConstraints
    global tpn tabUnDo
    global allowedArc
    global synchronized
    global parameters typePN cost couleurPN
    global declaration initialization timedCost nbTokenColor

    set tpn(courant) [calculTPNCourant 0]
    set nomDeBase [sansXml $nomRdP($tpn(onglet))]
    set fichier "$nomDeBase.cts" 
    export2CTS $tpn(courant) $fichier $formule $avecAffichage
}

proc numberOfLines {str} {
# return [regexp -all {[\n]+} $str]
# return [regexp -all {[$]+} $str]
#    puts [lsearch $str \n]
    return [expr [regexp -all {[\n]} $str] + 1]
}
 

proc export2CTS {letpn fichier formule avecAffichage} { 
    global tabPlace tabTransition tabConstraint 
    global nbProcesseur  
    global fin ok 
    global modif nomRdP
    global infini 
    global tabColor 
    global nbConstraints
    global tpn tabUnDo
    global allowedArc
    global synchronized
    global parameters typePN cost couleurPN
    global declaration initialization timedCost nbTokenColor
    global simulatorOn

    set retour [export2CTSgetError $letpn $fichier "$formule" -1 $avecAffichage]

}

proc export2CTSgetError {letpn fichier formule lineError avecAffichage} { 
    global tabPlace tabTransition tabConstraint 
    global nbProcesseur  
    global fin ok 
    global modif nomRdP
    global infini 
    global tabColor 
    global nbConstraints
    global tpn tabUnDo projet
    global allowedArc
    global synchronized
    global parameters typePN cost
    global declaration initialization transition timedCost nbTokenColor controle couleurPN
    global simulatorOn errorMessage
    global comptLine coma

    set errorMessage(section) ""
    set errorMessage(detail) ""
    set comptLine 0
    set localSpeed 1
    set localCost 0
    set InitParameters ""
    set InitMarking ""
    set initOnly  [lireInitially $declaration($letpn)]
    set newComptLine 0
    set comptLine 0
    
 #   set Initially "initially \{ $initOnly \n"

    
    if {[string compare $fichier ""] || ($lineError>0)} {

	if {$lineError<1} {
	    if {$avecAffichage} {
		affiche " \n" 
		affiche [mc "-Exporting net as "] 
		afficheBleu $fichier 
		affiche " ..." 
	    }
	    set File [open $fichier w] 
	    puts $File "\/\/ TPN name=$fichier\n"


	    if {$nbTokenColor($letpn)>0} {
	       puts $File "const int _romeo_colors = $nbTokenColor($letpn); \n"
	       puts $File "typedef int\[_romeo_colors\] place; \n"
#		puts $File "typedef int\[$nbTokenColor($letpn)\] place; \n"
	    } else {
		puts $File "typedef int place; \n"
	    } 
	    puts $File "\n[retirerInitially $declaration($letpn)]\n"
	    
	} else {
	    set newComptLine [expr $comptLine + [numberOfLines [retirerInitially $declaration($letpn)]]+3]


	    if {($lineError>$comptLine)&&($lineError<=$newComptLine)} {
		set  errorMessage(section) "Error in Functions and Types section (line [expr $lineError-$comptLine-1]):"
		set  errorMessage(detail) [retirerInitially $declaration($letpn)]
		if {$tpn(courant)==$letpn} {
		    ouvrirDeclaration [numOnglet $letpn] [sansXml $nomRdP([numOnglet $letpn])]
		}
            }
            set comptLine $newComptLine
	}

#--------------------------Charger les include files -------------------------
	if {$tpn(courant)==$letpn} {
	    set leOnglet $tpn(onglet)
	} else {
	    set leOnglet [numOnglet $letpn]
	}
	    
	set chemin [repertoire $nomRdP($tpn(onglet))]


	for {set i 1} {$i<=$projet($leOnglet,nbInclude)}  {incr i} { 

	    set fichierInclude "$chemin\/$projet($leOnglet,include,$i,file)"

#	    if { [catch {open $fichierInclude r} fid] } 
	    #puts "pas possible $fichierInclude $fid"

	    set includeFile [open $fichierInclude r]
	    set includedData [read $includeFile]
	    close $includeFile
	    
	    set initLocal [lireInitially $includedData]
	    if {$initLocal!=""} {set initOnly "$initOnly \n//******File: $projet($leOnglet,include,$i,file)\n$initLocal"}

	    if {$lineError<1} {
		puts $File "//******File: $projet($leOnglet,include,$i,file)\n[retirerInitially $includedData] \n"
	    } else {
		set newComptLine [expr $comptLine + [numberOfLines [retirerInitially $includedData]]+2]	
		
		if {($lineError>$comptLine)&&($lineError<=$newComptLine)} {
		    set laLigneInFile [expr $lineError-$comptLine-1]
		    set errorMessage(section) "Error in declaration. Line $laLigneInFile in file $projet($leOnglet,include,$i,file)\n"
		     set  errorMessage(detail) "Line $laLigneInFile in file: \n $fichierInclude"
		}
		 set comptLine $newComptLine
	    }
	}
	

	set comptLine [expr $comptLine + 1 ]
#************* Couleurs
 #      if {$nbTokenColor($letpn)>0} {
#	    if {$lineError<1} {
#	       puts $File "typedef int\[$nbTokenColor($letpn)\] place; \n"
#	    }	
#	       set comptLine [expr $comptLine + 1 ]   
 #      }
	
#************* Contraintes parametres
	
	if {$parameters >= 1 } {
	    set coma "parameters "
  	    for {set i 0} {$i<$nbConstraints($letpn)}  {incr i} { 
			if {[string length $tabConstraint($letpn,$i)] > 0} { 
			    set InitParameters "$InitParameters $coma $tabConstraint($letpn,$i)"
			    set coma "and"
			}
	    }
	    if {$lineError<1} {
		puts $File "$InitParameters \n \n" 
	    } else {
		
		if {($lineError>=$comptLine)&&($lineError<=$comptLine+3)} {
		     set errorMessage(section) "Error in Parameters initialization (line 1):"
		    set  errorMessage(detail) $InitParameters
		}
		set comptLine [expr $comptLine+3]
	    }
	}

	
#************* INITIALLY
	
	if {$lineError<1} {
	    puts $File "initially \{ $initOnly \n"
	} else {
	    set comptLine [expr $comptLine+1]
	    set newComptLine [expr $comptLine+ [numberOfLines $initOnly] ]
	
	    if {($lineError>$comptLine)&&($lineError<=$newComptLine)} {
		
		set  errorMessage(section) "Error in initialization section (line [expr $lineError-$comptLine]):"
		set  errorMessage(detail) $initOnly
	    
	    }
            set comptLine [expr $newComptLine]
	}



#*********************PLACES
	set coma ""
	set prefixe ""
	set InitMarking "[exportPlace2CTS $letpn $prefixe $coma]"
	set coma ","



	for {set i 1} {$i<=$projet($leOnglet,nbInput)}  {incr i} {
	    if {$projet($leOnglet,input,$i,status) != "deleted"} {
		set prefixe "[sansXml $projet($tpn(onglet),input,$i,file)]::"
		set leSlave [calculTPNCourant $i]
		set InitMarking "$InitMarking[exportPlace2CTS $leSlave $prefixe $coma]"
	    }
	}
	
	if {$InitMarking != ""} {set InitMarking "place $InitMarking;"}
	
       	if {$lineError<1} {
	    puts $File "$InitMarking \}\n" 
	} else {	
	    set newComptLine [expr $comptLine+ 1]
	    if {($lineError>$comptLine)&&($lineError<=$newComptLine)} {
		set  errorMessage(section) "Error in initialization section (line [expr $lineError-$comptLine]):"

		set  errorMessage(detail) " $initOnly \n $InitMarking;"
            }
            set comptLine [expr $newComptLine +1]
	}


#*********************TRANSITIONS
	set prefixe ""

	set dataTransition [exportTransition2CTS $letpn $prefixe $lineError]

	for {set i 1} {$i<=$projet($leOnglet,nbInput)}  {incr i} {
	    if {$projet($leOnglet,input,$i,status) != "deleted"} {
		set prefixe "[sansXml $projet($tpn(onglet),input,$i,file)]::"
		set leSlave [calculTPNCourant $i]
		set dataTransition "$dataTransition[exportTransition2CTS $leSlave $prefixe $lineError]"
	    }
	}


       	if {$lineError<1} {
	    puts $File "$dataTransition"
	}


	if {$lineError<1} {
	    if {$cost>0} {
		if {[sansEspace $timedCost($letpn)]==""} {
		    puts $File "\n  cost_rate 0"
		} else {
		    puts $File "\n  cost_rate $timedCost($letpn)"
		}
	    }
	    if {$formule == "noformula"} {
		puts $File "\n  \/\/ insert TCTL formula here : check formula"
	    } else {
		puts $File "\n $formule"
	    }
	    close $File 
	    if {$avecAffichage} { 
		affiche [mc "done"] 
	    }
	} elseif {$lineError>$comptLine} {
	    set errorMessage(section) "Error in TCTL formulae:"
	}
#	 set modif($tpn) 0 
         update idletasks
    }

    return "$errorMessage(section) @@details**$errorMessage(detail)" 
} 


proc guardVide {lagarde} {   

    if { [alphanumerique $lagarde] == ""} {
	return 1
    } else {
	return 0
    }
 }
#+++++++++++++++++++++ DECLARATION et INITIALIZATION +++++++++++++++++++++++++++ 

proc exportPlace2CTS {letpn prefixe coma} {   
    global tabPlace tabTransition tabConstraint 
    global nbProcesseur  
    global fin ok 
    global modif nomRdP
    global infini 
    global tabColor 
    global nbConstraints
    global tpn tabUnDo projet
    global allowedArc
    global synchronized
    global parameters typePN cost
    global declaration initialization transition timedCost nbTokenColor controle couleurPN
    global simulatorOn
    global comptLine

#    set nbTokenColor($letpn) 2

    set marquageInitial ""
    if {$nbTokenColor($letpn)>0} {

	for {set i 1} {$tabPlace($letpn,$i,statut)!=$fin} {incr i} { 
	    if {$tabPlace($letpn,$i,statut)==$ok} { 
		# on passe a identifier    AVANT :	set InitMarking "$InitMarking$coma [sansEspace $tabPlace($letpn,$i,label,nom)]'P$i=$tabPlace($letpn,$i,jeton)"

		set vectMarking ""
		set sepMarking ""
		set zero 0
		if {[nulMarking $tabPlace($letpn,$i,jeton)]} {
		    if {$nbTokenColor($letpn)>0} {
			for {set lacouleur 0} {$lacouleur < $nbTokenColor($letpn)} {incr lacouleur} { 
			    set vectMarking "$vectMarking$sepMarking$zero"
			    set sepMarking ","
			}
		    } else {
			set sepMarking "0"
		    }
		} else {
		    set vectMarking $tabPlace($letpn,$i,jeton)
		}
		
		set marquageInitial "$marquageInitial$coma $prefixe$tabPlace($letpn,$i,id)=\{$vectMarking\}"
	      	set coma ","
	    } 
	}
    } else {
       	for {set i 1} {$tabPlace($letpn,$i,statut)!=$fin} {incr i} { 
	    if {$tabPlace($letpn,$i,statut)==$ok} { 
		# on passe a identifier    AVANT :	set InitMarking "$InitMarking$coma [sansEspace $tabPlace($letpn,$i,label,nom)]'P$i=$tabPlace($letpn,$i,jeton)"
		if {$tabPlace($letpn,$i,jeton)==""} {
		    set marquageInitial "$marquageInitial$coma $prefixe$tabPlace($letpn,$i,id)=0"
		} else {
		    set marquageInitial "$marquageInitial$coma $prefixe$tabPlace($letpn,$i,id)=$tabPlace($letpn,$i,jeton)"
		}
	      	set coma ","
	    } 
	}
    }
    return $marquageInitial

}

proc exportTransition2CTS {letpn prefixe lineError} {   
    global tabPlace tabTransition tabConstraint 
    global nbProcesseur  
    global fin ok 
    global modif nomRdP
    global infini 
    global tabColor 
    global nbConstraints
    global tpn tabUnDo projet
    global allowedArc
    global synchronized
    global parameters typePN cost
    global declaration initialization transition timedCost nbTokenColor controle couleurPN
    global simulatorOn errorMessage
    global comptLine

    set resultat ""

    set accMin "\["
    set accMax "\]"

  #  set errorMessage(section) ""
  #  set errorMessage(detail) ""
    
    #if {$nbTokenColor($letpn)<=1} 
    if {$nbTokenColor($letpn)<1} {

	for {set i 1} {$tabTransition($letpn,$i,statut)!=$fin}  {incr i} { 
	       if {$tabTransition($letpn,$i,statut)==$ok} { 
		  set CTSwhen "$tabTransition($letpn,$i,guard)"
		  if {[guardVide $CTSwhen] == 1} { 
		      set CTSwhen ""
		      set coma "" 
		  } else { 
		      set CTSwhen "($CTSwhen)"
		      set coma " and " 
		  }
#		  set CTSdo "$tabTransition($letpn,$i,update)"
		  set CTSdo ""
		  set coma2 ""
		  set CTSintermediate ""
		  set coma3 ""
		  set listeP [list ]
		  set localSpeed 1
		  set localCost 1
		  for {set j 1} {$tabTransition($letpn,$i,Porg,$j) >0}   {incr j} { 
# l'indice de la place est $tabTransition($letpn,$i,Porg,$j)
		     if {[lsearch $listeP $tabTransition($letpn,$i,Porg,$j)] < 0} { 
		      set listeP [linsert $listeP  0 $tabTransition($letpn,$i,Porg,$j)]
		      # creation des listes des arcs entre  $i et $tabTransition($letpn,$i,Porg,$j)

		      set alertReset 0
		      set localIntermediate ""
		      set localWhen ""
		      set localDo ""
  	              for {set k 1} {$tabTransition($letpn,$i,Porg,$k) >0}  {incr k} { 
			  if {$tabTransition($letpn,$i,Porg,$k) == $tabTransition($letpn,$i,Porg,$j)} {
			     

			  #----------------- arc normal
			      if {($tabTransition($letpn,$i,PorgType,$k)==0)} {

				  set localWhen "$prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id) >= $tabTransition($letpn,$i,PorgWeight,$k)$coma$localWhen"
				  set coma " and "
				  set localIntermediate "$localIntermediate - $tabTransition($letpn,$i,PorgWeight,$k)"
				
			      }

#----------------- read arc : intermediate ne change pas

			      if {(($tabTransition($letpn,$i,PorgType,$k)==2)&&($allowedArc(read)==1))} {
			 
				  set localWhen "$prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id) >= $tabTransition($letpn,$i,PorgWeight,$k)$coma$localWhen"
				  set coma " and "
			      }

#----------------- reset arc : pas de when mais intermediate vide la place
			      if {(($tabTransition($letpn,$i,PorgType,$k)==1)&&($allowedArc(reset)==1))} {

				  set alertReset 1
			      }


#----------------- logicInhibitor : intermediate ne change pas when : < au lieu de >=
			      if {(($tabTransition($letpn,$i,PorgType,$k)==3)&&($allowedArc(logicInhibitor)==1))} {

				  set localWhen "$prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id) < $tabTransition($letpn,$i,PorgWeight,$k)$coma$localWhen"
				  set coma " and "
			      }
#----------------- timedInhibitor : ne change pas when intermediate et do mais determine speed

			      if {(($tabTransition($letpn,$i,PorgType,$k)==4)&&($allowedArc(timedInhibitor)==1))} {
				 	  
				  if {$tabTransition($letpn,$i,PorgInhibitingCondition,$k) != ""} {
				      set localSpeed "min($localSpeed, max(0, max($tabTransition($letpn,$i,PorgWeight,$k)-$prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id),1-([retirerAndOr $tabTransition($letpn,$i,PorgInhibitingCondition,$k)]))))"
				  } else {
				      set localSpeed "min($localSpeed,max(0,$tabTransition($letpn,$i,PorgWeight,$k)-$prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id)))"
				  }
			      }

			  } 

		      }
		      if {$localWhen != ""} {set CTSwhen "$localWhen$CTSwhen"}

# Determiner si la place est aussi une place destination de la transition --> orgEtDes
		      for {set k 1} {($tabTransition($letpn,$i,Pdes,$k) >0)&&($tabTransition($letpn,$i,Pdes,$k)!=$tabTransition($letpn,$i,Porg,$j))}   {incr k} {}
		      if {$tabTransition($letpn,$i,Pdes,$k) == $tabTransition($letpn,$i,Porg,$j)} {set orgEtDes $k} else {set orgEtDes -1}


#  AFFECTATIONS
		      if {$alertReset==1} {
		          set CTSintermediate  "$CTSintermediate $coma3 $prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id) = 0"

			  if {$orgEtDes>-1} {
			      set CTSdo "$CTSdo $coma2 $prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Pdes,$k),id) =  $tabTransition($letpn,$i,PdesWeight,$k)"
			  } else {
			      set CTSdo "$CTSdo $coma2 $prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id) = 0"
			  }

			  set coma3 ","
			  set coma2 ","

		      } else {


			  if {$localIntermediate!=""} {
			      set CTSintermediate  "$CTSintermediate $coma3 $prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id) =  $prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id) $localIntermediate"
			      set coma3 ","
			  }

			  if {$orgEtDes>-1} {
			      set CTSdo  "$CTSdo $coma2 $prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id) =  $prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id) $localIntermediate +  $tabTransition($letpn,$i,PdesWeight,$k)"
			  } else {
			      set CTSdo  "$CTSdo $coma2 $prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id) = $prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id) $localIntermediate"
			  }
			  set coma2 ","

		      }
		  


		    } 	

		 }
		 for {set j 1} {$tabTransition($letpn,$i,Pdes,$j) >0}   {incr j} { 
# l'indice de la place est $tabTransition($letpn,$i,Pdes,$j)
		     if {[lsearch $listeP $tabTransition($letpn,$i,Pdes,$j)] < 0} { 
			 set CTSdo "$CTSdo $coma2 $prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Pdes,$j),id) = $prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Pdes,$j),id) + $tabTransition($letpn,$i,PdesWeight,$j)"
			set coma2 ","
		    }
		 } 	

		 if {($controle==1)||($typePN==0)} {
		       set eft 0
		       set lft "inf"
		       set accMin "\["
		       set accMax ")"
		 } elseif {$parameters < 1 } {
		     set eft $tabTransition($letpn,$i,dmin) 
		     set accMin [crochetOF 1 $tabTransition($letpn,$i,eftIncl)]
		    if {$tabTransition($letpn,$i,dmax)==$infini} { 
			set lft "inf"
			set accMax ")" 
		    } else { 
			set lft $tabTransition($letpn,$i,dmax)
			set accMax [crochetOF 0 $tabTransition($letpn,$i,lftIncl)]
		    } 
		 } else {
		    if {$tabTransition($letpn,$i,minparam)==""} { 
			set eft "0" 
			set accMin "\["
		    } else { 
			set eft $tabTransition($letpn,$i,minparam)
			set accMin [crochetOF 1 $tabTransition($letpn,$i,eftIncl)]			
		    }	
		    if {$tabTransition($letpn,$i,maxparam)==""} { 
			set lft "inf" 
			set accMax ")"
		    } else { 
			set lft $tabTransition($letpn,$i,maxparam) 
			set accMax [crochetOF 0 $tabTransition($letpn,$i,lftIncl)]
		    }	
		 }

		   if {($controle>1)} {
		       set accMin "\["
		       set accMax "\]"
		   }
		   
	         if {$lineError<1} {
		     set resultat "$resultat transition"
#		     puts -nonewline $File "transition "
	         }

		 
		 if  {$typePN==-3} {
		     set localSpeed $localSpeed*($tabTransition($letpn,$i,speed))
		 }

		 set localCost $tabTransition($letpn,$i,cost)
		 if {[sansEspace $localCost]==""} {
		     set localCost 0
		 }

		 set resultatInter ""
		 if {($tabTransition($letpn,$i,unctrl)>=1) || ($CTSintermediate != "") || ($localSpeed != 1) || ($localCost != 0)|| ($tabTransition($letpn,$i,priority)!=0)} { 
		     if {$lineError<1} {
			 set resultatInter " \["
			 set comma ""
			 if {$tabTransition($letpn,$i,unctrl)>=1} {
			     set unctrlType "u"
			     if {$tabTransition($letpn,$i,unctrl)==2} { set unctrlType "ud"}
			     if {$tabTransition($letpn,$i,unctrl)==3} { set unctrlType "uf"}
			     if {$tabTransition($letpn,$i,unctrl)==4} { set unctrlType "ufd"}

			     set resultatInter "$resultatInter control=$unctrlType"
			     set comma "," 
			 }
			 if {($localCost != 0)&&($cost>0)} {
			     set resultatInter "$resultatInter$comma cost=$localCost"
			     set comma "," 
			 }
			 if {$tabTransition($letpn,$i,priority)!=0} {
			     set resultatInter "$resultatInter$comma priority=$tabTransition($letpn,$i,priority)"
			     set comma "," 
			 }	 
			 if {$CTSintermediate != ""} { 
			     set resultatInter "$resultatInter$comma intermediate \{ $CTSintermediate; \}"; 
			     set comma "," 
			 } 
			 if {$localSpeed != 1} {
			     set resultatInter "$resultatInter$comma speed= $localSpeed "
			 }
			set resultatInter "$resultatInter\] "
		    } 
	       }

	       if {[sansEspace $resultatInter]== "\[\]" } {
		   set resultatInter ""
	       }
	       set resultat "$resultat$resultatInter"

	       set comptLine [expr $comptLine + 1]
		 
	       if {$lineError<1} {

		     set resultat "$resultat $prefixe$tabTransition($letpn,$i,id) $accMin$eft,$lft$accMax"
		     if {[sansEspace $CTSwhen] == ""} { set CTSwhen "true"  }

		     if {$CTSdo != ""} {
			 set CTSdo "$CTSdo; $tabTransition($letpn,$i,update)"
		     } else {
			 set CTSdo "$tabTransition($letpn,$i,update)"
		     }

		     set resultat "$resultat\n      when ($CTSwhen)"
		     set resultat "$resultat\n      { $CTSdo }\n"
#		     puts $File  "\n"
		 } else {
		     if {[guardVide $tabTransition($letpn,$i,guard)] == 0} {
#		     if {[sansEspace $tabTransition($letpn,$i,guard)] != ""} 
			 set newComptLine [expr $comptLine+[numberOfLines $tabTransition($letpn,$i,guard)]]
			 if {($lineError>=$comptLine)&&($lineError<=$newComptLine)} {
			     set errorMessage(section) "Error in guard of transition $prefixe$tabTransition($letpn,$i,id) \"$tabTransition($letpn,$i,label,nom)\" (line [expr $lineError-$comptLine+1]):"
			     set errorMessage(detail) $tabTransition($letpn,$i,guard)
			     .romeo.global.frame.c itemconfig transition($i) -fill red
			 }
			 set comptLine [expr $newComptLine]
		     } else {
			 set comptLine [expr $comptLine +1]
		     }
		     
		     if {[sansEspace $tabTransition($letpn,$i,update)] != ""} {
			 set newComptLine [expr $comptLine+[numberOfLines $tabTransition($letpn,$i,update)]]
			 if {($lineError>=$comptLine)&&($lineError<=$newComptLine+1)} {
			     set errorMessage(section) "Error in update of transition $prefixe$tabTransition($letpn,$i,id) \"$tabTransition($letpn,$i,label,nom)\" (line [expr $lineError-$comptLine+1]):"
			     set errorMessage(detail) $tabTransition($letpn,$i,update)
			     .romeo.global.frame.c itemconfig transition($i) -fill red
			 }
			 set comptLine $newComptLine
		     } else {
			 set comptLine [expr $comptLine +1]
		     }
#		     set comptLine [expr $comptLine +1]


	         }

	       } 
	       # endif transition ok		

	}
	# endfor

	# ********************************************************************************************
	# LA MEME CHOSES AVEC LES COULEURS ********************************************************************************************
	# ********************************************************************************************
	
    } else {


	
	for {set i 1} {$tabTransition($letpn,$i,statut)!=$fin}  {incr i} {

	    if {$tabTransition($letpn,$i,statut)==$ok} {

		set CTSdo ""
		set CTSintermediate ""
		set localSpeed 1
		set coma2 ""
		set coma3 ""
		for {set laTokenColor -1} {$laTokenColor<$nbTokenColor($letpn)} {incr laTokenColor} {
		    set listePorgColor($laTokenColor) [list ]
		    set coloredIntermediate($laTokenColor) ""
		    set coloredWhen($laTokenColor) ""
		    set coloredDo($laTokenColor) ""
		    set alertReset($laTokenColor) 0
		    set listePorgColor($laTokenColor) [list ]

		    set listePorgResetColor($laTokenColor) [list ]

		}
	

	#	  set boucle "\$i = 0, 2 \n"  

		
		set CTSwhen "$tabTransition($letpn,$i,guard)"
		
		if {[guardVide $CTSwhen] == 1} { 
		    set CTSwhen ""
		    set coma "" 
		} else { 
		    set CTSwhen "($CTSwhen)"
		    set coma " and " 
		}

		set CTSdo ""
		#set CTSdo "$tabTransition($letpn,$i,update)"
		


		  
		set listeP [list ]

		set localCost 1
		set anyColor 0
		set acolor 0
		set anyList [list ]
		  
		for {set j 1} {$tabTransition($letpn,$i,Porg,$j) >0}   {incr j} { 
		      # l'indice de la place est $tabTransition($letpn,$i,Porg,$j)

		    if {$tabTransition($letpn,$i,PorgTokenColor,$j)==-1} {
			set anyColor 1
		    } else {
			set aColor $tabTransition($letpn,$i,PorgTokenColor,$j)
		    }		      
		    set laTokenColor $tabTransition($letpn,$i,PorgTokenColor,$j)
		    if {$laTokenColor==-1} {
			set coloredIndex "\$any"
		    } else {
			set coloredIndex $laTokenColor
		    }

		    
		    # creation des listes des arcs avec la couleur entre  $i et $tabTransition($letpn,$i,Porg,$j)

		    if {[lsearch $listeP $tabTransition($letpn,$i,Porg,$j)] < 0} { 
			  # creation des listes des arcs sans la couleur entre  $i et $tabTransition($letpn,$i,Porg,$j)
			set listeP [linsert $listeP  0 $tabTransition($letpn,$i,Porg,$j)]
		    }			 

	



		    #----------------- arc normal
		    if {($tabTransition($letpn,$i,PorgType,$j)==0)} {

			set listePorgColor($laTokenColor) [linsert $listePorgColor($laTokenColor)  0 $tabTransition($letpn,$i,Porg,$j)]
			set CTSwhen "$prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id)\[$coloredIndex\] >= $tabTransition($letpn,$i,PorgWeight,$j)$coma$CTSwhen"
			set coma " and "
			set coloredlIntermediate($laTokenColor) "$coloredIntermediate($laTokenColor) - $tabTransition($letpn,$i,PorgWeight,$j)"
			
		    }

#----------------- read arc : intermediate ne change pas

		    if {(($tabTransition($letpn,$i,PorgType,$j)==2)&&($allowedArc(read)==1))} {

			 
			set CTSwhen "$prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id)\[$coloredIndex\] >= $tabTransition($letpn,$i,PorgWeight,$j)$coma$CTSwhen"
			set coma " and "
		    }

#----------------- reset arc : pas de when mais intermediate vide la place
		    if {(($tabTransition($letpn,$i,PorgType,$j)==1)&&($allowedArc(reset)==1))} {

			set listePorgResetColor($laTokenColor) [linsert $listePorgResetColor($laTokenColor)  0 $tabTransition($letpn,$i,Porg,$j)]
			set alertReset($laTokenColor) 1
		    }


#----------------- logicInhibitor : intermediate ne change pas when : < au lieu de >=
		    if {(($tabTransition($letpn,$i,PorgType,$j)==3)&&($allowedArc(logicInhibitor)==1))} {

			set CTSwhen "$prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id)\[$coloredIndex\] < $tabTransition($letpn,$i,PorgWeight,$j)$coma$CTSwhen"
			set coma " and "
		    }
#----------------- timedInhibitor : ne change pas when intermediate et do mais determine speed 

		    if {(($tabTransition($letpn,$i,PorgType,$j)==4)&&($allowedArc(timedInhibitor)==1))} {
				 	  
			if {[sansEspace $tabTransition($letpn,$i,PorgInhibitingCondition,$j)] != ""} {
			    set localSpeed "min($localSpeed, max(0, max($tabTransition($letpn,$i,PorgWeight,$j)-$prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id)\[$coloredIndex\],1-([retirerAndOr $tabTransition($letpn,$i,PorgInhibitingCondition,$j)]))))"
			} else {
			    set localSpeed "min($localSpeed,max(0,$tabTransition($letpn,$i,PorgWeight,$j)-$prefixe$tabPlace($letpn,$tabTransition($letpn,$i,Porg,$j),id)\[$coloredIndex\]))"
			}
		    }

		} 

		# On fait tous les arcs Porg MAINTENANT LA SUITE
		
		#		      if {$localWhen != ""} {}

		    
		for {set laTokenColor -1} {$laTokenColor<$nbTokenColor($letpn)} {incr laTokenColor} {
		    set CTSwhen "$coloredWhen($laTokenColor)$CTSwhen"
		}
		
		for {set k 1} {$tabTransition($letpn,$i,Pdes,$k) >0}   {incr k} {

		    # Pour toutes les places destination de la transition i

		    set laPlaceDes $tabTransition($letpn,$i,Pdes,$k)
		    set laTokenColor  $tabTransition($letpn,$i,PdesTokenColor,$k)
		    if {$laTokenColor==-1} {
			if {$anyColor == 1 } {
			    set coloredIndex "\$any"
			} else {
			    # si il y a any en destination alors qu'il n'y avait pas any en source on prend une des couleurs d'un arc amont
			    set coloredIndex "\$any"
			    set anyColor 1
			    #"$aColor"
			}
		    } else {
			set coloredIndex $laTokenColor
		    }

		    
#  AFFECTATIONS 
		    if {[lsearch $listePorgResetColor($laTokenColor) $laPlaceDes] >= 0} {

			# la place est aussi la source d'un reset 
			
			set listePorgResetColor($laTokenColor)  [lremove $listePorgResetColor($laTokenColor) $laPlaceDes]
			set listePorgColor($laTokenColor)  [lremove $listePorgColor($laTokenColor) $laPlaceDes]
			
			set CTSintermediate  "$CTSintermediate $coma3 $prefixe$tabPlace($letpn,$laPlaceDes,id)\[$coloredIndex\] = 0"
			set CTSdo "$CTSdo $coma2 $prefixe$tabPlace($letpn,$laPlaceDes,id)\[$coloredIndex\] =  $tabTransition($letpn,$i,PdesWeight,$k)"
			set coma3 ","
			set coma2 ","
			 
		    } elseif {[lsearch $listePorgColor($laTokenColor) $laPlaceDes] >= 0} { 
			
			# laplace est à la fois source et destination d'un arc normal

			set listePorgColor($laTokenColor)  [lremove $listePorgColor($laTokenColor) $laPlaceDes]
			
			set CTSintermediate  "$CTSintermediate $coma3 $prefixe$tabPlace($letpn,$laPlaceDes,id)\[$coloredIndex\] =  $prefixe$tabPlace($letpn,$laPlaceDes,id)\[$coloredIndex\] - [retrouverLePoidsArcPT $letpn $laPlaceDes $i 0]"
			set CTSdo "$CTSdo $coma2 $prefixe$tabPlace($letpn,$laPlaceDes,id)\[$coloredIndex\] =  $prefixe$tabPlace($letpn,$laPlaceDes,id)\[$coloredIndex\] - [retrouverLePoidsArcPT $letpn $laPlaceDes $i 0] + $tabTransition($letpn,$i,PdesWeight,$k) "

			set coma3 ","
			set coma2 ","

		    } else {
			# laplace est seulement un place destination
			set CTSdo "$CTSdo $coma2 $prefixe$tabPlace($letpn,$laPlaceDes,id)\[$coloredIndex\] =  $prefixe$tabPlace($letpn,$laPlaceDes,id)\[$coloredIndex\] + $tabTransition($letpn,$i,PdesWeight,$k) "
			set coma2 ","
		    }			    
		}

	

		# Pour les places qui sont seulement des places sources
		for {set laTokenColor -1} {$laTokenColor<$nbTokenColor($letpn)} {incr laTokenColor} {
		    if {$laTokenColor==-1} {
			set coloredIndex "\$any"
		    } else {
			set coloredIndex $laTokenColor
		    }
		    # arc normal
		    for {set indiceLPO 0} {$indiceLPO < [llength $listePorgColor($laTokenColor)]}   {incr indiceLPO} {

			set indiceDeLaPlace [lindex $listePorgColor($laTokenColor) $indiceLPO]
			set nomPlace $prefixe$tabPlace($letpn,$indiceDeLaPlace,id)
			set CTSdo "$CTSdo $coma2 $nomPlace\[$coloredIndex\] =  $nomPlace\[$coloredIndex\] - [retrouverLePoidsArcPT $letpn $indiceDeLaPlace $i 0] "
			set CTSintermediate "$CTSintermediate $coma3 $nomPlace\[$coloredIndex\] =  $nomPlace\[$coloredIndex\] - [retrouverLePoidsArcPT $letpn $indiceDeLaPlace $i 0] "
			set coma3 ","
			set coma2 ","	
		    }

		    # arc reset
		    for {set indiceLPO 0} {$indiceLPO < [llength $listePorgResetColor($laTokenColor)]}   {incr indiceLPO} {

			set indiceDeLaPlace [lindex $listePorgResetColor($laTokenColor) $indiceLPO]
			set nomPlace $prefixe$tabPlace($letpn,$indiceDeLaPlace,id)
			set CTSdo "$CTSdo $coma2 $nomPlace\[$coloredIndex\] = 0"
			set CTSintermediate "$CTSintermediate $coma3 $nomPlace\[$coloredIndex\] = 0 "
			set coma3 ","
			set coma2 ","	
		    }
		    		
		}		
				
	     	
	    
	

	# on reprend le code normal
	
	    if {($controle==1)||($typePN==0)} {
		set eft 0
		set lft "inf"
		set accMin "\["
		set accMax ")"
	    } elseif {$parameters < 1 } {
		set eft $tabTransition($letpn,$i,dmin) 
		set accMin [crochetOF 1 $tabTransition($letpn,$i,eftIncl)]
		if {$tabTransition($letpn,$i,dmax)==$infini} { 
		    set lft "inf"
		    set accMax ")"
		} else { 
		    set lft $tabTransition($letpn,$i,dmax)
		    set accMax [crochetOF 0 $tabTransition($letpn,$i,lftIncl)]
		} 
	    } else {
		if {$tabTransition($letpn,$i,minparam)==""} { 
		    set eft "0" 
		    set accMin "\["
		} else { 
		    set eft $tabTransition($letpn,$i,minparam) 
		    set accMin [crochetOF 1 $tabTransition($letpn,$i,eftIncl)]
		}	
		if {$tabTransition($letpn,$i,maxparam)==""} { 
		    set lft "inf" 
		    set accMax ")"
		} else { 
		    set lft $tabTransition($letpn,$i,maxparam) 
		    set accMax [crochetOF 0 $tabTransition($letpn,$i,lftIncl)]
		}	
	    }
		
	    if {($controle>1)} {
		set accMin "\["
		set accMax "\]"
	    }
		    
	    if {$lineError<1} {
		if {$anyColor == 1 } {
		    set resultat "$resultat for \$any = 0, _romeo_colors -1 \{ transition"
#		    set resultat "$resultat for \$any = 0, [expr $nbTokenColor($letpn)-1] \{ transition"
		    #		     puts -nonewline $File "transition "
		} else {
		    set resultat "$resultat transition"		    
		}
	    }
	    
	    
	    if  {$typePN==-3} {
		set localSpeed $localSpeed*($tabTransition($letpn,$i,speed))
	    }

	    set localCost $tabTransition($letpn,$i,cost)
		
	    set resultatInter ""
	    if {($tabTransition($letpn,$i,unctrl)>=1) || ([sansEspace $CTSintermediate] != "") || ($localSpeed != 1) || ($localCost != 0) || ($tabTransition($letpn,$i,priority)!=0)} { 
		if {$lineError<1} {
		    set resultatInter "$resultatInter \["
		    set comma ""
		    if {$tabTransition($letpn,$i,unctrl)>=1} {
			set unctrlType "u"
			if {$tabTransition($letpn,$i,unctrl)==2} { set unctrlType "ud"}
			if {$tabTransition($letpn,$i,unctrl)==3} { set unctrlType "uf"}
			if {$tabTransition($letpn,$i,unctrl)==4} { set unctrlType "ufd"}
			
			set resultatInter "$resultatInter control=$unctrlType"
			set comma "," 
		    }
		    if {($localCost != 0)&&($cost>0)} {
			set resultatInter "$resultatInter$comma cost=$localCost"
			set comma "," 
		    }
		    if {$tabTransition($letpn,$i,priority)!=0} {
			set resultatInter "$resultatInter$comma priority=$tabTransition($letpn,$i,priority)"
			set comma "," 
		    }
		    if {[sansEspace $CTSintermediate] != ""} { 
			set resultatInter "$resultatInter$comma intermediate \{ $CTSintermediate; \}"; 
			set comma "," 
		    } 
		    if {$localSpeed != 1} {
			set resultatInter "$resultatInter$comma speed= $localSpeed "
		    }
		    set resultatInter "$resultatInter\] "
		} 
	    }
	    if {[sansEspace $resultatInter]== "\[\]" } {
		set resultatInter ""
	    }
	    set resultat "$resultat$resultatInter"
		
	    if {$anyColor == 1 } {
		set ajouterUneLigne 1
	    } else {
		set ajouterUneLigne 0
	    }
	    set comptLine [expr $comptLine + $ajouterUneLigne +  1]

	    
	    if {$lineError<1} {

		set resultat "$resultat $prefixe$tabTransition($letpn,$i,id) $accMin$eft,$lft$accMax"
		if {[sansEspace $CTSwhen] == ""} { set CTSwhen "true"  }

		if {$CTSdo != ""} {
		    set CTSdo "$CTSdo; $tabTransition($letpn,$i,update)"
		} else {
		    set CTSdo "$tabTransition($letpn,$i,update)"
		}

		set resultat "$resultat\n      when ($CTSwhen)"
		set resultat "$resultat\n      { $CTSdo }\n"

		if {$anyColor == 1 } {
		    set resultat "$resultat\} \n"
		}
		#		     puts $File  "\n"
	    } else {
		if {[guardVide $tabTransition($letpn,$i,guard)] == 0} {
		    #		     if {[sansEspace $tabTransition($letpn,$i,guard)] != ""} 
		    set newComptLine [expr $comptLine+[numberOfLines $tabTransition($letpn,$i,guard)]]
		    if {($lineError>=$comptLine)&&($lineError<=$newComptLine)} {
			set errorMessage(section) "Error in guard of transition $prefixe$tabTransition($letpn,$i,id) \"$tabTransition($letpn,$i,label,nom)\" (line [expr $lineError-$comptLine+1]):"
			set errorMessage(detail) $tabTransition($letpn,$i,guard)
			.romeo.global.frame.c itemconfig transition($i) -fill red
		    }
		    set comptLine [expr $newComptLine]
		} else {
		    set comptLine [expr $comptLine+1]
		}


	
		
		
		if {[sansEspace $tabTransition($letpn,$i,update)] != ""} {
		    set newComptLine [expr $comptLine+[numberOfLines $tabTransition($letpn,$i,update)]]
		    if {($lineError>=$comptLine)&&($lineError<=$newComptLine)} {
			set errorMessage(section) "Error in update of transition $prefixe$tabTransition($letpn,$i,id) \"$tabTransition($letpn,$i,label,nom)\" (line [expr $lineError-$comptLine+1]):"
			set errorMessage(detail) $tabTransition($letpn,$i,update)
			.romeo.global.frame.c itemconfig transition($i) -fill red
		    }
		    set comptLine [expr $newComptLine]
		} else {
		    set comptLine [expr $comptLine + 1]
		}

		#		     set comptLine [expr $comptLine +1]
	    }
	}
	}
    }

    return $resultat
}



proc lremove {listVariable value} {

    return [lsearch -all -inline -not -exact $listVariable $value]
}

# type : PlaceTransition=0 flush=1 read=2 logicalInhibitor=3 timedInhibitor=4
proc retrouverLePoidsArcPT {letpn indicedP indicedT typeArc} {   
    global tabPlace tabTransition 
    global fin ok

    set result 0

    for {set i 1} {$tabTransition($letpn,$indicedT,Porg,$i) >0}   {incr i} {
	if {($tabTransition($letpn,$indicedT,Porg,$i)==$indicedP)&&($tabTransition($letpn,$indicedT,PorgType,$i)==$typeArc) } {
		set result $tabTransition($letpn,$indicedT,PorgWeight,$i)
	}
    }
    return $result
}


proc retirerAndOr {chaine} {
    # remplace AND OR par * +

    set chaine [string map {) ") "} $chaine]
    set chaine [string map {( " ("} $chaine]
    set chaine [string map {or +} $chaine]
    set chaine [string map {OR +} $chaine]
    set chaine [string map {and *} $chaine]
    set chaine [string map {AND *} $chaine]
    return $chaine
 }

proc crochetOF {min included} {
    	if {$min==1} {
	    if {$included==1} {
		return "\["
	    } else {
		return "("
	    }
       	} elseif {$included==1} {
	    return "\]"
	} else {
	    return ")"
	}
}
