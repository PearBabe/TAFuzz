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




# tpn(courant) =  $tpn(onglet)*100 + $tabUnDo($tpn(onglet),courant)

#retrouve le numero de l'onglet auquel appartient le TPN unTPN :
proc numOnglet {unTPN} {
# unTPN est un entier donc expr renvoie un entier
    return [expr $unTPN/10000]
}

proc existOnglets {nameT} {
global listeOnglets

 if {[lsearch $listeOnglets(tpn) $nameT] > -1} { 
     set indice [lsearch $listeOnglets(tpn) $nameT]
     return [lindex $listeOnglets(indice) $indice]
 } else { return -1}

}


proc changeNameOngletCourant {w nouveauNom} {
    global listeOnglets
    global tpn tabUnDo nomRdP



  set indice [lsearch $listeOnglets(indice) $tpn(onglet)]
#  set ancienNom [lindex $listeOnglets(tpn) $indice]
  set nomRdP($tpn(onglet)) $nouveauNom 

  set listeOnglets(tpn) [lreplace $listeOnglets(tpn) $indice $indice $nouveauNom]


  if {$tpn(onglet)>=0} {
      $w.onglet.onglet$tpn(onglet).idTPN configure -text [nomSeul $nouveauNom] -command "changerOngletCourant $w {$nouveauNom}"
  } else {
    nouvelOnglet $w $nouveauNom 
  }

  redessinerRdP $w.frame.c
}


proc alone {liste} {

# alone si il y a 0 ou 1 elements dans la liste
    if {[llength $liste]<2} {
      return 1
    } else {
      return 0
    }
}

proc nouvelOnglet {w unTPN} {
global listeOnglets 
global tpn tabUnDo projet viewOnglet
global simulatorOn 
global firstVisible


 if {$simulatorOn==1} {
    affiche "\n "
    affiche [mc "-Warning: Not allowed - Quit simulator first"]
  } else {
    set newIndice 0
    if {[llength $listeOnglets(indice)]>0} {
	$w.onglet.onglet$tpn(onglet).idTPN configure -state normal 
	$w.onglet.onglet$tpn(onglet).declaration configure -state disabled  
	$w.onglet.onglet$tpn(onglet).init configure -state disabled 
    }

      
    if {[lsearch $listeOnglets(tpn) $unTPN] < 0} { 
       while {[lsearch $listeOnglets(indice) $newIndice] > -1} {
          incr newIndice 
        }
        set listeOnglets(tpn) [linsert $listeOnglets(tpn)  0 $unTPN]
        set listeOnglets(indice) [linsert $listeOnglets(indice)  0 $newIndice]
 
      
        set tpn(onglet) $newIndice
        set tpn(slave) 0
	set firstVisible($tpn(onglet)) 1

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


	set tabUnDo([expr $tpn(onglet)*100],taille) 1
	set tabUnDo([expr $tpn(onglet)*100],courant) 0

# Il peut y avoir 100 esclaves
	for {set i 1} {$i<=99}  {incr i} { 
	    set tabUnDo([expr $tpn(onglet)*100+$i],taille) 1
	    set tabUnDo([expr $tpn(onglet)*100+$i],courant) 0
	}

	set tpn(courant) [calculTPNCourant 0]
#        set projet($tpn(onglet),nbInclude) 0 

	frame $w.onglet.onglet$newIndice 
        button $w.onglet.onglet$newIndice.idTPN -text [nomSeul $unTPN] -font menufont -command "changerOngletCourant $w {$unTPN}" -state disabled 
	button $w.onglet.onglet$newIndice.init -text "Project" -font menufont -command "ouvrirProjet $tpn(onglet) [nomSeul $unTPN]"  -bd 0 -relief flat -overrelief raised
	button $w.onglet.onglet$newIndice.declaration -text "Declaration" -font menufont -command "ouvrirDeclaration $tpn(onglet) [nomSeul $unTPN]"  -bd 0 -relief flat -overrelief raised
 
#       grid $w.onglet.onglet$newIndice 
        pack configure $w.onglet.onglet$newIndice.idTPN -side top -fill x
        pack configure $w.onglet.onglet$newIndice.init $w.onglet.onglet$newIndice.declaration -side left -expand true -fill x
        pack configure $w.onglet.onglet$newIndice -side left 
     }
  } 
#$w.onglet configure -background yellow -bd 2
}

#----------------------------------
# unTPN est le nom complet du reseau de Petri
proc delOnglet {w unOnglet} {
global listeOnglets
global tpn tabUnDo
global simulatorOn 

 if {$simulatorOn==1} {
    affiche "\n "
    affiche [mc "-Warning: Not allowed - Quit simulator first"]
  } else {
    set indice [lsearch $listeOnglets(tpn) $unOnglet]
    set numBouton [lindex $listeOnglets(indice) $indice]

    if {$indice > -1} { 
        set listeOnglets(tpn) [lreplace $listeOnglets(tpn) $indice $indice]
        set listeOnglets(indice) [lreplace $listeOnglets(indice) $indice $indice]
     } 

     destroy $w.onglet.onglet$numBouton
  }

}

#----------------------------------
# nouveauTPN est le nom complet du reseau de Petri
proc changerOngletCourant {w nouveauTPN} {
global tpn tabUnDo projet viewOnglet
global listeOnglets
global simulatorOn 


 if {$simulatorOn==1} {
    affiche "\n "
    affiche [mc "-Warning: Not allowed - Quit simulator first"]
  } else {

    set ancienOnglet $tpn(onglet) 
    set viewOnglet(X,$ancienOnglet) [lindex [$w.frame.c xview] 0] 
    set viewOnglet(Y,$ancienOnglet) [lindex [$w.frame.c yview] 0]

    $w.onglet.onglet$tpn(onglet).idTPN configure -state normal
    $w.onglet.onglet$tpn(onglet).declaration configure -state disabled 
    $w.onglet.onglet$tpn(onglet).init configure -state disabled 

    set indice [lsearch $listeOnglets(tpn) $nouveauTPN]
    set tpn(onglet) [lindex $listeOnglets(indice) $indice]
    set tpn(slave) 0 
    set tpn(courant) [calculTPNCourant 0]


    $w.onglet.onglet$tpn(onglet).idTPN configure -state disabled  
    $w.onglet.onglet$tpn(onglet).declaration configure -state normal 
    $w.onglet.onglet$tpn(onglet).init configure -state normal 

   if {[winfo exists .initialization$tpn(onglet)]} {
     # remonter la fenetre au premier plan
     raise  .initialization$tpn(onglet)
    }
 
    if {[winfo exists .declaration$tpn(onglet)]} {
     # remonter la fenetre au premier plan
	raise .declaration$tpn(onglet)
    }

redessinerProjet $w 
#    redessinerRdP $w.frame.c
  }
}
#----------------------------------
# nouvelOngletCourant est l'indice du nouvelOnglet
proc basculeOngletCourant {nouvelOngletCourant} {
global tpn tabUnDo viewOnglet
global listeOnglets
global simulatorOn 


 if {$simulatorOn==1} {
    affiche "\n "
    affiche [mc "-Warning: Not allowed - Quit simulator first"]
  } else {
     set w .romeo.global


    $w.onglet.onglet$tpn(onglet).idTPN configure -state normal
    $w.onglet.onglet$tpn(onglet).declaration configure -state disabled 
    $w.onglet.onglet$tpn(onglet).init configure -state disabled 


    set ancienOnglet $tpn(onglet) 
    set viewOnglet(X,$ancienOnglet) [lindex [$w.frame.c xview] 0] 
    set viewOnglet(Y,$ancienOnglet) [lindex [$w.frame.c yview] 0]
  
    set tpn(onglet) $nouvelOngletCourant
    set tpn(slave) 0
    set tpn(courant) [calculTPNCourant 0]

    $w.onglet.onglet$tpn(onglet).idTPN configure -state disabled 
    $w.onglet.onglet$tpn(onglet).declaration configure -state normal 
    $w.onglet.onglet$tpn(onglet).init configure -state normal 

    if {[winfo exists .initialization$tpn(onglet)]} {
     # remonter la fenetre au premier plan
     raise  .initialization$tpn(onglet)
     colorationSyntaxique .initialization$tpn(onglet).text 
    }
 
    if {[winfo exists .declaration$tpn(onglet)]} {
     # remonter la fenetre au premier plan
	raise .declaration$tpn(onglet)
	colorationSyntaxique .declaration$tpn(onglet).text 
    }

      redessinerProjet $w
#    redessinerRdP $w.frame.c
  }
}

#----------------------------------
# nouvelOngletCourant est l'indice du nouvelOnglet
proc basculeOngletCourantSiNecessaire {nouvelOngletCourant} {
global tpn tabUnDo
global listeOnglets
global simulatorOn 


 if {$nouvelOngletCourant!=$tpn(onglet)} {
     basculeOngletCourant $nouvelOngletCourant
  }
}



proc fermerOngletCourrant {w c} {
global tpn tabUnDo
global listeOnglets
global simulatorOn 

 if {$simulatorOn==1} {
    affiche "\n "
    affiche [mc "-Warning: Not allowed - Quit simulator first"]
  } else {

  if {[fautIlSauver]} {
     set indice [lsearch $listeOnglets(indice) $tpn(onglet)]
     set listeOnglets(tpn) [lreplace $listeOnglets(tpn) $indice $indice]
     set listeOnglets(indice) [lreplace $listeOnglets(indice) $indice $indice]
     destroy $w.onglet.onglet$tpn(onglet)
     if {[winfo exists .declaration$tpn(onglet)]} {
	 destroy .declaration$tpn(onglet)
     }
     if {[winfo exists .initialization$tpn(onglet)]} {
	 destroy .initialization$tpn(onglet)
     }
     if {[llength $listeOnglets(indice)]>0} {
        set tpn(onglet) [lindex $listeOnglets(indice) 0]
	set tpn(slave) 0 
	set tpn(courant) [calculTPNCourant 0]

        $w.onglet.onglet$tpn(onglet).idTPN configure -state disabled
	$w.onglet.onglet$tpn(onglet).declaration configure -state normal 
	$w.onglet.onglet$tpn(onglet).init configure -state normal             
        redessinerProjet $w
     } else {
        nouveauRdP $w $c
     }
   }
 }
}

proc ouvrirOnglet {w c} {
global listeOnglets
global tpn tabUnDo modif
global simulatorOn cheminFichiers
global parikhVector
global tabPlace tabTransition fin projet


 if {$simulatorOn==1} {
    affiche "\n "
    affiche [mc "-Warning: Not allowed - Quit simulator first"]
  } else {
     set types {{"TPN file"     {.xml}      TEXT}}

      set file [tk_getOpenFile -initialdir $cheminFichiers -filetypes $types ]

     if {[string compare $file ""]} {
       if {[existCarDansMot [nomSeul $file] " "]} {
           afficheRouge "\n-Warning:"
	   affiche " The Space caracter is not allowed in file name ->"
	   afficheBleu " [nomSeul $file]"
       } elseif {[existOnglets $file]>-1} {
            affiche "\n -Warning: $file is already opened"
       } else {
            if {$tpn(onglet)>0} {
		$w.onglet.onglet$tpn(onglet).idTPN configure -state disabled 
		$w.onglet.onglet$tpn(onglet).declaration configure -state normal 
		$w.onglet.onglet$tpn(onglet).init configure -state normal             
	    }
            ouvrirPointXML $w $c 0 $file
	    if {[existOnglets "noName.xml"]>-1} {
		set indice [lsearch $listeOnglets(tpn) "noName.xml"]
		set numOnglet [lindex $listeOnglets(indice) $indice]
		set numTPN [expr $numOnglet*10000 + $tabUnDo([expr $numOnglet*100],courant)] 
#		set numTPN [expr [lindex $listeOnglets(indice) $indice]*100+$tabUnDo($tpn(courant),courant)]
		if {($tabTransition($numTPN,1,statut)==$fin)&&($tabPlace($numTPN,1,statut)==$fin)} {
		    delOnglet $w noName.xml
		}
	    }    
       }
     }
      if {[winfo exists fenetrePNdrawing]} {
	  raise .fenetrePNdrawing
	  focus -force .fenetrePNdrawing
      }
  }
}


proc ouvrirDeclaration {leOnglet leNomTPN} {
    global declaration 
    global tpn tabUnDo
    global modif fontSizeEditor
    global projet


 modifTPN $tpn(courant)

set leTPN [calculTPNCourant 0] 
#[expr $leOnglet*100 + $tabUnDo($leOnglet,courant)]

 if {[winfo exists .declaration$leOnglet]} {
     # remonter la fenetre au premier plan
     raise .declaration$leOnglet
 } else {

     set fdec .declaration$leOnglet
     catch {destroy $fdec}
     toplevel $fdec
#     wm protocol $fdec WM_DELETE_WINDOW {puts "glop"}
	
#	wm geometry $f +$x+$y
     wm title $fdec "Functions & Types - $leNomTPN"
	
  #  font create textFont -family Courier -size 10

  event add <<undo>> <Control-Z> <Control-z> <Command-Z> <Command-z>
  bind .declaration$leOnglet <<undo>> "unDoModifDeclarIni $leOnglet"
  bind .declaration$leOnglet <Button-1> "basculeOngletCourantSiNecessaire $leOnglet"



     font configure fontEditor -family Courrier -size $fontSizeEditor

     text $fdec.text -yscrollcommand "$fdec.scroll set" -setgrid true \
	-width 60 -height 40 -wrap word -bg white -font fontEditor
     scrollbar $fdec.scroll -command "$fdec.text yview" 

     pack $fdec.scroll -side right -fill y 
     pack $fdec.text -expand yes -fill both 



     $fdec.text insert end $declaration($leTPN)

      configureCouleur $fdec.text
      colorationSyntaxique $fdec.text

bind  $fdec.text <Button-1> "colorationSyntaxique $fdec.text"
bind  $fdec.text <Return> "colorationSyntaxique $fdec.text"
bind  $fdec.text <space> "colorationSyntaxique $fdec.text"
bind  $fdec.text <Key> "colorationSyntaxique $fdec.text"


     frame $fdec.buttons
     pack $fdec.buttons -side bottom -fill x -pady 2m
#     button $fdec.buttons.annuler -text "Cancel" -command  "destroy $fdec"
     button $fdec.buttons.quitter -text "Close"  -command  "valideclarQuit $fdec $leOnglet"
#     button $fdec.buttons.accepter -default active -text " Save without closing" \
#		-command "valideclar $fdec $leOnglet"
#     pack $fdec.buttons.accepter 
     pack  $fdec.buttons.quitter   -side left -expand 1
 }
 } 
  



proc unDoModifDeclarIni {leOnglet} {
global declaration 
global modif
global tpn tabUnDo

    if {$tpn(onglet)!=$leOnglet} {
	basculeOngletCourant $leOnglet
    }
#unDoModif .romeo.global.frame.c

}

proc valideclarOnglet {leOnglet leTPN} {
global declaration 
global modif
global tpn tabUnDo

if {[winfo exists .declaration$leOnglet]} {
# set declaration($leTPN) [.declaration$leOnglet.text get 1.0 {end -1c}]
 set declaration($leTPN) [.declaration$leOnglet.text get 1.0 end]

}
}


proc valideclar {fenetre leOnglet} {
global declaration 
global modif
global tpn tabUnDo

    if {$tpn(onglet)!=$leOnglet} {
	basculeOngletCourant $leOnglet
    }
#set declaration($leTPN) [$fenetre.text get 1.0 end]
# set leTPN [expr $leOnglet*100 + $tabUnDo($leOnglet,courant)]


    colorationSyntaxique $fenetre.text

modifTPN [calculTPNdeOnglet $leOnglet]
}

proc valideclarQuit {fenetre leOnglet} {
global declaration 
global modif
global tpn tabUnDo

    if {$tpn(onglet)!=$leOnglet} {
	basculeOngletCourant $leOnglet
    }
modifTPN [calculTPNdeOnglet $leOnglet]
destroy $fenetre
}


proc ouvrirProjet {leOnglet leNomTPN} {
   global projet tpn tabUnDo cheminFichiers nomRdP 
   global modif fontSizeEditor
   global firstVisible
   global nbTokenColor nbCouleurLocal couleurLocal ancienCouleurLocal
   global simulatorOn

# *****************************************
  modifTPN [calculTPNdeOnglet $leOnglet]


 if {[winfo exists .projet$leOnglet]} {
     # remonter la fenetre au premier plan
     raise  .projet$leOnglet
 } else {
	set leProjet .projet$leOnglet
	catch {destroy $leProjet}
	toplevel $leProjet
#        wm protocol $fini WM_DELETE_WINDOW {}

#	wm geometry $f +$x+$y
     wm title $leProjet "Project - $leNomTPN"
	
#  event add <<undo>> <Control-Z> <Control-z> <Command-Z> <Command-z>
#  bind .initialization$leOnglet <<undo>> "unDoModifDeclarIni $leOnglet"
#  bind .initialization$leOnglet <Button-1> "basculeOngletCourantSiNecessaire $leOnglet"

   
     font configure fontEditor -family Courrier -size $fontSizeEditor

# PROJET*******************
#set i $declaration($leTPN,nbInclude)


#puts "$tpn(courant) -> $leTPN -> $i -> $projet($leTPN,fichier$i) "

     frame  .projet$leOnglet.projet -bd 2  -relief sunken

     frame  .projet$leOnglet.projet.nomProjet
     label  $leProjet.projet.nomProjet.text  -text "Project Name:  [nomSeul $nomRdP($tpn(onglet))]" -font menufont  -bg gray90
     pack $leProjet.projet.nomProjet.text -side left 
     pack $leProjet.projet.nomProjet -side top -fill x
     frame  .projet$leOnglet.projet.repertoire
     label  $leProjet.projet.repertoire.text  -text "Project Directory: [repertoire $nomRdP($tpn(onglet))]" -font menufont -bg gray90
     pack $leProjet.projet.repertoire.text -side left 
     pack $leProjet.projet.repertoire -side top -fill x


     frame  .projet$leOnglet.projet.include -bd 4  -relief sunken

# COLORED PETRI NETS


# couleurs
     set s "$leProjet.projet.include"
     frame $s.couleur -relief solid -bd 1
     pack $s.couleur -side top -pady 2 -anchor w -fill x
#     label $s.couleur.label
#     pack $s.couleur.label -side top -pady 2 -anchor w
#     $s.couleur.label config -text [mc "Colored PN:"]

     if {$nbTokenColor($tpn(courant)) >=1} {
	 set couleurLocal 1
	 set ancienCouleurLocal 1
	 set nbCouleurLocal $nbTokenColor($tpn(courant))
     } else {
	 set nbCouleurLocal 1
	 set ancienCouleurLocal 0
	 set couleurLocal 0
     }

#    checkbutton $s.couleur.couleurYes -text "Colored PN"  -variable couleurLocal \
#	-relief flat -anchor w -selectcolor red -command "validerCouleurPN $leOnglet $tpn(courant) $s.couleur.label"
    checkbutton $s.couleur.couleurYes -text "Colored PN" -font menufont -variable couleurLocal \
	-relief flat -anchor w -selectcolor red 
    pack $s.couleur.couleurYes -side top -pady 2 -anchor w

     entry $s.couleur.saisie -justify left -textvariable nbCouleurLocal -font menufont -relief sunken -width 7 -bg white
     label $s.couleur.label
     pack $s.couleur.label -side left
     pack $s.couleur.saisie -side left
     $s.couleur.label config -text "Color number ( $nbCouleurLocal ):  " -font menufont

     button $s.couleur.buttons -default active -text "  Ok  " -font menufont \
	    -command "validerCouleurPNandTerminate  $leProjet $leOnglet $tpn(courant) $s.couleur.label"

      
	
     pack $s.couleur.buttons  -side left -expand 1
     
     bind $leProjet <Return> "validerCouleurPNandTerminate  $leProjet $leOnglet $tpn(courant) $s.couleur.label"


     # LES INCLUDES

     
     label .projet$leOnglet.projet.include.titre  -text "Included Declaration file" -font menufont -bg LightYellow  -relief ridge  -bd 4 -width 50
     pack .projet$leOnglet.projet.include.titre -side top -fill x     
     
# BOUCLE pour ouvrir tous les includes

 for {set i 1} {$i<=$projet($leOnglet,nbInclude)}  {incr i} { 

     set file .projet$leOnglet.projet.include.fichier
     frame  $file$i -bd 2 

     label  $file$i.nom  -text $projet($leOnglet,include,$i,file) -font menufont -bg gray90 -justify left 
     label $file$i.label 
     pack $file$i.label -side left  -fill x
     pack $file$i.nom -side left  -fill x

     $file$i.label config -text "----> " -font menufont

    button $file$i.delete -text "Remove" -font menufont  -command  "removeInclude $i $leOnglet $leNomTPN" 
    pack $file$i.delete  -side right 
#    button $file$i.open -text "Open" -command  "openInclude $i $leOnglet" 
#    pack $file$i.open  -side right 

    pack $file$i -side top -fill x

 }

    button $leProjet.projet.include.browse -text "Add new File" -font menufont -command  "includeFile $leOnglet $leNomTPN"
    pack $leProjet.projet.include.browse  -side right -expand 1 

# Fin boucle FOR

#  -----------------INPUT PETRI NET --------------

     frame  .projet$leOnglet.projet.input -bd 4 -relief sunken 
     label .projet$leOnglet.projet.input.titre  -text "Slave Petri Net" -font menufont -bg LightYellow -relief ridge  -bd 4 -width 50
     pack .projet$leOnglet.projet.input.titre -side top -fill x

 frame  $leProjet.projet.input.lesboutons  -relief ridge  -bd 4
     pack  $leProjet.projet.input.lesboutons -side top -expand 1 
     
# BOUCLE pour ouvrir tous les input

 #    set nbInputVisible 0
  fenetreInput $leOnglet $leNomTPN  
 #    for {set i 1} {$i<=$projet($leOnglet,nbInput)}  {incr i} { 

  #    if {$projet($leOnglet,input,$i,status) != "deleted"} {

#	 set nbInputVisible [expr $nbInputVisible+1]
	  
#	 set filePN .projet$leOnglet.projet.input.fichierPN
#	 frame  $filePN$i -bd 2 
#
#	 label  $filePN$i.nom  -text $projet($leOnglet,input,$i,file) -bg gray90 -justify left 
#	 label $filePN$i.label 
#	 pack $filePN$i.label -side left  -fill x
#	 pack $filePN$i.nom -side left  -fill x

#	 $filePN$i.label config -text "----> "
#
#	 if {($nbInputVisible >=$firstVisible($leOnglet))&&($nbInputVisible <=$firstVisible($leOnglet)+15)} {
	 
#	     button $filePN$i.delete -text "Remove" -command  "removeInput $i $leOnglet $leNomTPN" 
#	     pack $filePN$i.delete  -side right 
#	     button $filePN$i.reload -text "Reload" -command  "reloadInput $i $leOnglet $leNomTPN" -state normal
#	     pack $filePN$i.reload  -side right 
#	     button $filePN$i.close -text "Close" -command  "closeInput $i $leOnglet" -state disabled
#	     pack $filePN$i.close  -side right 
#	     button $filePN$i.open -text "Open" -command  "openInput $i $leOnglet" -state normal
#	     pack $filePN$i.open  -side right 


#	     if {$projet($leOnglet,input,$i,status) == "open"} {
#		 $filePN$i.open  configure -state disabled
#		 $filePN$i.close  configure -state normal
#	     }
	 
#	     pack $filePN$i -side top -fill x
#	 }
 #     }

  #   }

  

     # Fin boucle FOR

    
     
  button $leProjet.projet.input.lesboutons.browse -text "Import PN" -font menufont -command "importPN $leOnglet $leNomTPN"
    pack $leProjet.projet.input.lesboutons.browse  -side right -expand 1

    button $leProjet.projet.input.lesboutons.next -text "Next" -font menufont -command "nextVisible $leOnglet $leNomTPN"
    pack $leProjet.projet.input.lesboutons.next  -side right -expand 1

    button $leProjet.projet.input.lesboutons.previous -text "Previous" -font menufont -command "previousVisible $leOnglet $leNomTPN"
     pack $leProjet.projet.input.lesboutons.previous  -side right -expand 1
     
pack .projet$leOnglet.projet.include -side left
pack .projet$leOnglet.projet.input -side right
pack .projet$leOnglet.projet -side left


#**************************
#     text $fini.text -yscrollcommand "$fini.scroll set" -setgrid true \
#	-width 60 -height 40 -wrap word -bg white -font fontEditor
#     scrollbar $fini.scroll -command "$fini.text yview" 

#     pack $fini.scroll -side right -fill y 
#     pack $fini.text -expand yes -fill both 

#set leTPN [expr $leOnglet*100 + $tabUnDo($leOnglet,courant)]

#     $fini.text insert end $initialization($leTPN)

#     configureCouleur $fini.text
     

#      colorationSyntaxique $fini.text

#bind  $fini.text <Button-1> "colorationSyntaxique $fini.text"
#bind  $fini.text <Return> "colorationSyntaxique $fini.text"
#bind  $fini.text <space> "colorationSyntaxique $fini.text"     
#bind $fini.text <Key> "colorationSyntaxique $fini.text" 

     frame $leProjet.buttons
     pack $leProjet.buttons -side bottom -fill x -pady 2m
     button $leProjet.buttons.quitter -text "Close" -font menufont -command  "valideIniQuit $leProjet $leOnglet" 

     pack $leProjet.buttons.quitter  -side left -expand 1
  }
} 


proc fenetreInput {leOnglet leNomTPN} {
   global projet nomRdP 
   global firstVisible

#le projet .projet$leOnglet


#frame  .projet$leOnglet.projet.input -bd 4 -relief sunken
#set fenProjet .projet$leOnglet.projet.input

 #    label $fenProjet.titre  -text "Slave Petri Net" -bg LightYellow -relief ridge  -bd 4 -width 50
  #   pack $fenProjet.titre -side top -fill x

# BOUCLE pour ouvrir tous les input

    frame .projet$leOnglet.projet.input.fichierPN
     pack .projet$leOnglet.projet.input.fichierPN -side top  -fill x
    
     set nbInputVisible 0
     
     for {set i 1} {$i<=$projet($leOnglet,nbInput)}  {incr i} { 

      if {$projet($leOnglet,input,$i,status) != "deleted"} {

	 set nbInputVisible [expr $nbInputVisible+1]
	  
	 set filePN .projet$leOnglet.projet.input.fichierPN.fichierPN
	 frame  $filePN$i -bd 2 

	 label  $filePN$i.nom  -text $projet($leOnglet,input,$i,file) -font menufont -bg gray90 -justify left 
	 label $filePN$i.label 
	 pack $filePN$i.label -side left  -fill x
	 pack $filePN$i.nom -side left  -fill x

	 $filePN$i.label config -text "----> "

	 if {($nbInputVisible >=$firstVisible($leOnglet))&&($nbInputVisible <=$firstVisible($leOnglet)+15)} {
	 
	     button $filePN$i.delete -text "Remove" -font menufont -command  "removeInput $i $leOnglet $leNomTPN" 
	     pack $filePN$i.delete  -side right 
	     button $filePN$i.reload -text "Reload" -font menufont -command  "reloadInput $i $leOnglet $leNomTPN" -state normal
	     pack $filePN$i.reload  -side right 
	     button $filePN$i.close -text "Close" -font menufont -command  "closeInput $i $leOnglet" -state disabled
	     pack $filePN$i.close  -side right 
	     button $filePN$i.open -text "Open" -font menufont -command  "openInput $i $leOnglet" -state normal
	     pack $filePN$i.open  -side right 


	     if {$projet($leOnglet,input,$i,status) == "open"} {
		 $filePN$i.open  configure -state disabled
		 $filePN$i.close  configure -state normal
	     }
	 
	     pack $filePN$i -side top -fill x
	 }
      }

     }

  #  button $fenProjet.browse -text "Import PN" -command "importPN $leOnglet $leNomTPN"
  #  pack $fenProjet.browse  -side right -expand 1

#    button $fenProjet.next -text "Next" -command "nextVisible $leOnglet $leNomTPN"
 #   pack $fenProjet.next  -side right -expand 1

  #  button $fenProjet.previous -text "Previous" -command "previousVisible $leOnglet $leNomTPN"
   # pack $fenProjet.previous  -side right -expand 1

}

proc nextVisible {onglet nomTPN} {
       global firstVisible

    set firstVisible($onglet) [expr  $firstVisible($onglet) + 5]

    destroy .projet$onglet.projet.input.fichierPN
    fenetreInput $onglet $nomTPN
}


proc previousVisible {onglet nomTPN} {
       global firstVisible

    set firstVisible($onglet) [expr  $firstVisible($onglet) - 5]
    if {$firstVisible($onglet) < 1} {set firstVisible($onglet) 1}

    destroy .projet$onglet.projet.input.fichierPN
    fenetreInput $onglet $nomTPN
}

proc valideIniOnglet {leOnglet leTPN} {
global initialization 
global modif
global tpn tabUnDo

 if {[winfo exists .initialization$leOnglet]} {
#     set initialization($leTPN) [.initialization$leOnglet.text get 1.0 {end -1c}]
     set initialization($leTPN) [.initialization$leOnglet.text get 1.0 end]
 }
}

proc valideIni {fenetre leOnglet} {
global initialization 
global modif
global tpn tabUnDo

    if {$tpn(onglet)!=$leOnglet} {
	basculeOngletCourant $leOnglet
    }

    colorationSyntaxique $fenetre.text

    modifTPN [calculTPNdeOnglet $leOnglet]
}

proc valideIniQuit {fenetre leOnglet} {
global initialization 
global modif
global tpn tabUnDo

    if {$tpn(onglet)!=$leOnglet} {
	basculeOngletCourant $leOnglet
    }
    modifTPN [calculTPNdeOnglet $leOnglet]
    destroy $fenetre
}

proc validerCouleurPN {leOnglet letpn affi} {
    global nbTokenColor nbCouleurLocal couleurLocal projet
    global simulatorOn
    global tabPlace InitialToken ok fin
    global tabTransition allowedArc controle


    if {$simulatorOn==0} {

	set nbCoul [format %d $nbCouleurLocal]
	if {($couleurLocal > 0)&&($nbCoul >= 1)} {
	    set nbTokenColor($letpn) $nbCoul
	} else {
	    set nbTokenColor($letpn) 0
	}
	
	$affi config -text "Color number ( $nbTokenColor($letpn) ):  " -font menufont
	
	forAllAjusterTailleMarking $nbTokenColor($letpn) $letpn
	ajusterLesCouleurs $nbTokenColor($letpn) $letpn
	
	for {set i 1} {$i<=$projet($leOnglet,nbInput)}  {incr i} {
	    if {$projet($leOnglet,input,$i,status) != "deleted"} {
		set leSlave [calculTPNCourant $i]
		
		if {$couleurLocal > 0} {
		    set nbTokenColor($leSlave) $nbTokenColor($letpn)
		} else {
		    set nbTokenColor($leSlave) 0
		}
		
		forAllAjusterTailleMarking $nbTokenColor($leSlave) $leSlave
		ajusterLesCouleurs $nbTokenColor($leSlave) $leSlave
	    }
	}

	modifTPN $letpn
	redessinerProjet .romeo.global
	
    }
}

proc validerCouleurPNandTerminate {leProjet leOnglet letpn affi} {
    global nbTokenColor nbCouleurLocal couleurLocal projet ancienCouleurLocal
    global simulatorOn

    if {$simulatorOn==0} {
	if {$ancienCouleurLocal != $couleurLocal} {
	    checkDejaOuvert
	}
	validerCouleurPN $leOnglet $letpn $affi
	valideIniQuit $leProjet $leOnglet
    }
}
