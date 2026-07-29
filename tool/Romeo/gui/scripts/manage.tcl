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

# parsing de projets

#********************** lire la valeur d'un attribut *********************

#proc lireAttribut {liste attribut defaut} {
#    if {[lsearch $liste $attribut]!=-1} {
#	return [lindex $liste [expr [lsearch $liste $attribut]+1]]
#    } else {return $defaut}
#}

#********************** ouverture de balise *****************************



proc erreurManage {balise attendu} {
    .romeo.frame.c configure -cursor ""
    update
    affiche "\n *error : \"$balise\" founded"
    error "\"$balise\" founded ??? not a $attendu file"
    set button [tk_messageBox -icon error -message "this file isn't a $attendu file"]
}



#*****************************************parse property *********************************************

proc elementDebutProperty {nomBalise attributs } {
    global theProperty
    global ligneProperty
    
    switch $nomBalise {
	instance {
	    set instanceName [lireAttribut $name id 0]
	    set tpnFile [lireAttribut $ton op 0]
	}
	synchronization {
            set synchronized [lireAttribut $attributs listSynch 0]
	}
	default { 
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
	instance {
	}
	synchronization {
	}
	default {
	}
    }
}


proc ouvrirProjet {} {
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


proc quitterProjectManager {fenetre} {
saveProject $fenetre
destroy $fenetre
}

#--------------------------------------------------------------------------------------
# ********************** CREATION DE LA FENETRE D'EDITION DU TPN **************************

proc openProject {} {
    global versionRomeo
    
    # pour cacher la fenetre principale
    wm withdraw .

    set mp .manage
    catch {destroy $mp}

    #hack pour une vraie barre de menu :p
    toplevel $mp
# -menu .romeo_menu 
    
    #  wm visual $r best
    wm title $mp "Romeo Project Manager"
    wm iconname $mp "Romeo"
    #focus -force.romeo
	wm geometry $mp +0+25
    wm protocol $mp WM_DELETE_WINDOW {quitterProjectManager .manage}
    set m $mp.global
    #  $w config  

    set fm $m.frame.c
    frame $m
    pack $m -side left -expand yes -fill both


    #++++++++++++++ creation de la deuxieme barre du haut
    frame $m.barreHaut 
    pack $m.barreHaut -side top -expand 0


    button $m.barreHaut.insert -text [mc "Add Template instance"] -command "addTemplate $fm " 
    pack configure $m.barreHaut.insert -side left -padx 5

    button $m.barreHaut.addsynch -text [mc "Add synchronization"] -command "addSynchro $fm 0" 
    pack configure $m.barreHaut.addsynch -side left -padx 5


    if {[catch {package require BWidget}]} {
    } else {
	set boxOpen [ButtonBox $m.barreHaut.boxOpen -spacing 0 -padx 1 -pady 1]
	$boxOpen add -image [Bitmap::get new] \
	    -highlightthickness 0 -takefocus 0 -relief link -borderwidth 1 -padx 1 -pady 1 \
	    -helptext [mc "Create a new project"] -command "newProject $m $fm"
	$boxOpen add -image [Bitmap::get open] \
	    -highlightthickness 0 -takefocus 0 -relief link -borderwidth 1 -padx 1 -pady 1 \
	    -helptext [mc "Open an existing project"] -command "openProject $m $fm 0 0"
	$boxOpen add -image [Bitmap::get save] \
	    -highlightthickness 0 -takefocus 0 -relief link -borderwidth 1 -padx 1 -pady 1 \
	    -helptext [mc "Save project"] -command "saveProject $m"
	pack $boxOpen -side left -anchor w

	set sep [Separator $m.barreHaut.sep -orient vertical]
	pack $sep -side left -fill y -padx 4 -anchor w
    }

#    creerBoutonZoom $m $m.barreHaut
    
    # ++++++++++++++++++++ Creation de la Barre de gauche graphique +++++++++++++++++++++++++++

    #[package version BWidget]
    frame $m.barreGauche 
    pack $m.barreGauche -side left -expand 0



    canvas $m.barreGauche.sep -width 20 -height 5 
    pack $m.barreGauche.sep -side top


    # ++++++++++++++++ Creation de la fenetre d'affichage ++++++++++++++++++
#    frame $m.out  
#    pack $m.out -side bottom -fill x -padx 1
#
#    text $m.out.texte -yscrollcommand "$m.out.vscroll set" -width 100 -height 6 -bg white -wrap word
#    scrollbar $m.out.vscroll -command "$m.out.texte yview"  
#    pack $m.out.texte -side left -fill both -expand yes
#    pack $m.out.vscroll -side right -fill y
#    affiche \
#"--------------------------------------------------------------------------------------------
# $versionRomeo  Copyright (c) All rights reserved                                            
#                                                                                            
# IRCCyN (Institut de Recherche en Communications et CybernÃ©tique de Nantes) - UMR CNRS 6597
#--------------------------------------------------------------------------------------------"

# creation du canvas et des ascenceurs ()rappel c = w.frame.c)

  ascenceur $m $fm

  newProject $m $fm
#******************Racourci commande + click sur la fenetre : creation
}


proc ascenceur {w c} {

set maxXP 10000
set maxYP 10000

 #   destroy $w.frame
    frame $w.frame 
    pack $w.frame -side top -fill both -expand yes

    # rappel c = w.frame.c


    set liste [list 0 0 [expr $maxXP] [expr $maxYP]]
    canvas $c -scrollregion $liste -width 550 -height 350 \
	-relief sunken -borderwidth 2 \
	-xscrollcommand "$w.frame.hscroll set" \
	-yscrollcommand "$w.frame.vscroll set" 
    scrollbar $w.frame.vscroll -command "$c yview" 
    scrollbar $w.frame.hscroll -orient horiz -command "$c xview" 

    # dessin des ascenceurs :

    grid $c -in $w.frame \
	-row 0 -column 0 -rowspan 1 -columnspan 1 -sticky news
    grid $w.frame.vscroll \
	-row 0 -column 1 -rowspan 1 -columnspan 1 -sticky news
    grid $w.frame.hscroll \
	-row 1 -column 0 -rowspan 1 -columnspan 1 -sticky news
    grid rowconfig    $w.frame 0 -weight 1 -minsize 0
    grid columnconfig $w.frame 0 -weight 1 -minsize 0

    # ++++++ le fond blanc
#    $c config -bg white

    set font1 {Times 12}
    set font2 {Helvetica 24 bold}
}




# --------------------------------------------------------------------------------------------------
# -------------------------------------------- GESTION DU PROJET -----------------------------------
# --------------------------------------------------------------------------------------------------
proc saveProject {fm} {
    global cheminFichiers
    global project
    set types {{"Project file"     {.proj}      TEXT}}
    set fichier [tk_getSaveFile -initialdir $cheminFichiers -filetypes $types ]
     if {[string compare $fichier ""]} {

	    set File [open $fichier w] 
	    # ajout guillaume => histoire que les "parseurs" XML savent quoi "parser" 
	    puts $File "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>" 
	    puts $File "<Project name=\"$fichier\">" 


     }

}

proc newProject  {f fm} {
global tpn
global nomRdP
global project

    set project(liste) [list]
    set project(name) "noName.proj"
    set project(nbTPN) 0
    set project(1,name) tpn1
    set project(parse) 1


    $fm addtag projectTAG withtag [$fm create rect 10 10 200 2000 -width 2 -outline black \
				     -fill white]
    $fm addtag projectTAG2 withtag [$fm create rect 200 10 2000 400 -width 2 -outline black \
				     -fill white]
    $fm addtag effaceBarre withtag [$fm create rect 195 12 205 398 -width 2 -outline white \
				     -fill white]

    set projectName [$fm create text 12 25 -text  $project(name) -fill blue4 -font {Times 14 bold underline} -anchor w]
    $fm addtag nameTAG withtag $projectName
    $fm bind nameTAG <Any-Enter> "anyEnterRed $fm"
    $fm bind nameTAG <Any-Leave> "anyLeaveBlue $fm "
    $fm bind nameTAG <Button-3> "addTemplate $fm"
    $fm bind nameTAG <Button-2> "addTemplate $fm"
    $fm bind nameTAG <Double-Button-1> "addTemplate $fm"

}

proc doubleClickProj {c} {


}
proc anyEnterRed {c} {
	$c itemconfig current -fill red
}

proc anyLeaveBlue {c} {
	$c itemconfig current -fill blue4
}

proc addTemplate {fm} {
global tpn
global nomRdP
global project
    global cheminFichiers



    set types {{"TPN file"     {.xml}      TEXT}}
    set file [tk_getOpenFile -initialdir $cheminFichiers -filetypes $types ]
    if {[string compare $file ""]} {
      set i [expr $project(nbTPN) +1]
      set tpn $i
      set project(nbTPN) $i
      set namePossible "tpn$i"
      set prim "'"
      while {[existInstance $namePossible]} {set namePossible $namePossible$prim}
      set project($i,name) $namePossible
      set project($i,template) $file
      set project([expr $i+1],name) ""
      set project([expr $i+1],template) ""

      printTemplateInstance $fm $i
      parserPointXML $i  $project($i,template)
    }

}

proc printTemplateInstance {fm i} {
global project

      set templateName [$fm create text 20 [expr 25 + 40*$i] -text "|\n|-$project($i,name) \n   -> [nomSeul $project($i,template)]" -fill blue4  -font {Times 14} -anchor w]
      $fm addtag tpn$i withtag $templateName
      $fm bind tpn$i <Any-Enter> "anyEnterRed $fm"
      $fm bind tpn$i <Any-Leave> "anyLeaveBlue $fm"
      $fm bind tpn$i <Button-3> "modifTemplate $fm $i"
      $fm bind tpn$i <Button-2> "modifTemplate $fm $i"
      $fm bind tpn$i <Double-Button-1> "modifTemplate $fm $i"

}

proc modifTemplate {c numTPN} {
global tpn
global project

templateInstance $numTPN $c
#changeName $numTPN $c
}




#afficheIndiceTransition $fm.$i.transition
proc anyEnterInstance {f fm} {
}

proc lireTPN {numTPN} {
    global env
    global nomRdP
    global modif
    global home
    global cheminFichiers
    global francais
    global tabPlace
    global tabTransition
    global tabConstraint
    global nbConstraints
    global nbProcesseur
    global fin ok destroy
    global synchronized

 parserPointXML $numTPN 0

}



proc templateInstance {numTPN fn} {
global project 
global nouveauNom
set nouveauNom  $project($numTPN,name) 
    set in .instanceName$numTPN
    catch {destroy $in}
    toplevel $in

    frame $in.listeSynchro  -relief ridge -bd 4
    label $in.template 
    $in.template config -text "Template :  $project($numTPN,template) " 
    pack $in.template -side top

    frame $in.instance
    pack $in.instance -side top -fill x
    label $in.instance.name
    $in.instance.name config -text "Name :  $project($numTPN,name)"
    pack $in.instance.name -side left 
    entry $in.instance.saisieNom -justify left -textvariable nouveauNom -relief sunken -width 30 -bg white

    pack  $in.instance.saisieNom  -side left 

    frame $in.buttons
    pack $in.buttons -side bottom 
    button $in.buttons.delete -text " Delete Instance " -command  "deleteInstance $numTPN $fn $in"
    button $in.buttons.annuler -text " Cancel " -command  "destroy $in"
    button $in.buttons.accepter -default active -text "  Ok  " -command "validerChangeName $numTPN $fn $in"

    pack  $in.buttons.delete  $in.buttons.accepter $in.buttons.annuler  -side left 
    bind $in <Return> "validerChangeName $numTPN $fn $in"

}


proc deleteInstance {numTPN can fen} {
global project 

   set project(parse) 0

for {set i $numTPN} {$i < $project(nbTPN)} {incr i} {
    set project($i,name) $project([expr $i+1],name)
    set project($i,template) $project([expr $i+1],template)
  $can delete tpn$i
    printTemplateInstance $can $i
}
  $can delete tpn$project(nbTPN)
set project(nbTPN) [expr $project(nbTPN)-1]

destroy $fen


}

proc existInstance {nameInstance} {
global project
set oui 0
    for {set i 1} {$i < $project(nbTPN)} {incr i} {
           if {![string compare $project($i,name) $nameInstance]} {
               set  oui 1
           }
    }
return $oui
}

proc validerChangeName {numTPN can fen} {
global project 
global nouveauNom
set  good 1

    set nouveauNom [sansEspace $nouveauNom]
    for {set i 1} {$i < $project(nbTPN)} {incr i} {
	if {$i!=$numTPN} {
           if {![string compare $project($i,name) $nouveauNom]} {
               set  good 0
           }
	}
    }
    if {$good==1} {  
       reecrireLesSynchros  $project($numTPN,name) $nouveauNom
       set project($numTPN,name) $nouveauNom
       $can delete tpn$numTPN 
       printTemplateInstance $can $numTPN
       
       destroy $fen
    } else {
	  set button [tk_messageBox -icon error -message  "instance $nouveauNom already exists"]
    }

}

# --------------------------------------------------------------------------------------------------
#-------------------------------------LES SYNCHRONISATIONS -----------------------------------------
# --------------------------------------------------------------------------------------------------


proc validerSynchro {fm fd} {
global project 
global currentSynch
global labelSynch

  set currentSynch [lreplace $currentSynch 0 0 $labelSynch]
  set currentSynch [ordonneVect $currentSynch]
    if {[synchExisteDeja $currentSynch]} {
       effacerSyncro $fm
       deleteSynchroDeLaListeWithoutLabel $currentSynch
       afficherToutesLesSynchros $fm
    }

    if {[alone $currentSynch]==0} {

      set i [llength $project(liste)]
      lappend project(liste) $currentSynch
      set synchName [$fm create text 200 [expr 35 + 20*$i] -text [affUnVectSynch $currentSynch] -fill blue4  -font {Times 14} -anchor w]
      $fm addtag synch$i withtag $synchName
      $fm bind synch$i <Any-Enter> "anyEnterRed $fm"
      $fm bind synch$i <Any-Leave> "anyLeaveBlue $fm"
#      $fm bind synch$i <Button-3> "modifTemplate $fm $i"
      $fm bind synch$i <Button-2>  "addSynchro $fm [list $currentSynch]" 
      $fm bind synch$i <Double-Button-1> "addSynchro $fm [list $currentSynch]" 
  } 
  destroy $fd

}


proc deleteSynchro {fm fd vecteurADetruire} {
global project
  effacerSyncro $fm
  set indiceVecteur [isInSynch $project(liste) $vecteurADetruire]
  set project(liste) [lreplace $project(liste) $indiceVecteur $indiceVecteur]
  destroy $fd
  afficherToutesLesSynchros $fm
}

proc deleteSynchroDeLaListe {vecteurADetruire} {
global project
  set indiceVecteur [isInSynch $project(liste) $vecteurADetruire]
  set project(liste) [lreplace $project(liste) $indiceVecteur $indiceVecteur]
}

proc deleteSynchroDeLaListeWithoutLabel {vecteurADetruire} {
global project
  set indiceVecteur [isInSynchWithoutLabel $project(liste) $vecteurADetruire]
  set project(liste) [lreplace $project(liste) $indiceVecteur $indiceVecteur]
}


proc affUnVectSynch {liste} {
set affic ""
puts "yo $liste"
#l'indice 0 c'est le label de la synchro donc on commence à 1
    for {set i 1} {$i<[llength $liste]} {set i [expr $i+2]} {
puts "$i : [lindex $liste $i]"
     if {$i>1} {  set affic "$affic and"}
     set affic "$affic  [lindex $liste $i].[lindex $liste [expr $i+1]]"
 }
set affic "$affic  ->  [lindex $liste 0]"
 return $affic
}

proc affUneSynch {liste} {
    set untpn [lindex $liste 0]
    set uneT  [lindex $liste 1]
    return $untpn.$uneT
}


#--------- ouverture de la fenetre pertmettant de definir et d'ajouter une synchro
proc addSynchro {fm vecteurSynch} {

global tabTransition tpn 
global leVecteur
global listeSynchLocal
global tabSynchLocal
global fin ok
global project 
global currentSynch
global labelSynch

    if {$vecteurSynch==0} {
      set labelSynch "epsilon"
      set currentSynch [list]
     lappend currentSynch $labelSynch
    } else {
      set currentSynch $vecteurSynch
      set labelSynch  [lindex $vecteurSynch 0]
    }


    set synch .synchronizationVectors
    catch {destroy $synch}
    toplevel $synch

   frame $synch.frame
    pack $synch.frame -side left -expand yes -fill both



  frame $synch.frame.barre
    pack $synch.frame.barre -side top -expand 0  

    button $synch.frame.barre.cancel -text "cancel" -command "destroy $synch" 
    if {$vecteurSynch!=0} {
      button $synch.frame.barre.ok -text "add" -command "validerSynchro $fm $synch" 
	button $synch.frame.barre.delete -text "delete" -command "deleteSynchro $fm $synch [list $currentSynch]" 
      pack configure $synch.frame.barre.delete -side left -padx 5
    } else {
       button $synch.frame.barre.ok -text "ok" -command "validerSynchro $fm $synch" 
    }
    pack configure $synch.frame.barre.ok  $synch.frame.barre.cancel -side left -padx 5



    frame $synch.frame.labelSynch
    pack configure $synch.frame.labelSynch -side top -expand yes   -fill both


	entry $synch.frame.labelSynch.saisieNom -justify left -textvariable labelSynch -relief sunken -width 30 -bg white
	label $synch.frame.labelSynch.label
	pack $synch.frame.labelSynch.label -side left
	$synch.frame.labelSynch.label config -text Label:
	pack $synch.frame.labelSynch.saisieNom -side left


set sv $synch.frame.can
   frame $sv
    pack $sv -side top -fill both -expand yes

#set listeSynchro [list]


set liste [list 0 0 [expr 150*$project(nbTPN)+100] 2000]
    canvas $sv.c -scrollregion $liste -width 550 -height 350 \
	-relief sunken -borderwidth 2 \
	-xscrollcommand "$sv.hscroll set" \
	-yscrollcommand "$sv.vscroll set" 
    scrollbar $sv.vscroll -command "$sv.c yview" 
    scrollbar $sv.hscroll -orient horiz -command "$sv.c xview" 

    # dessin des ascenceurs :


    grid $sv.c -in  $sv \
	-row 0 -column 0 -rowspan 1 -columnspan 1 -sticky news
    grid $sv.vscroll \
	-row 0 -column 1 -rowspan 1 -columnspan 1 -sticky news
    grid $sv.hscroll \
	-row 1 -column 0 -rowspan 1 -columnspan 1 -sticky news
    grid rowconfig   $sv 0 -weight 1 -minsize 0
    grid columnconfig $sv 0 -weight 1 -minsize 0


    for {set i 1} {$i <= $project(nbTPN)} {incr i} {
       if {$project(parse)==0} { parserPointXML $i  $project($i,template)}


        $sv.c addtag legende1 withtag  [$sv.c create text  5 15 -text "Synchronization :" -fill black  -font {Times 12 bold underline} -anchor w]
        $sv.c addtag legende2 withtag  [$sv.c create text  5 45 -text "Instance Name :" -fill black  -font {Times 12 bold underline} -anchor w] 

        $sv.c addtag vecteurResult withtag  [$sv.c create rect 105 5 [expr 100+ $i*165] 20 -width 1 -fill white -outline white]


        afficheIndiceVector $sv.c $i
   }
   set project(parse) 1

   if {[llength $currentSynch]>0} {
     for {set i 1} {$i <= $project(nbTPN)} {incr i} {
        set indiceInstance [isInSynch $currentSynch $project($i,name)]
	if {$indiceInstance>-1} {
           affSynch $sv.c  $i [lindex $currentSynch [expr $indiceInstance+1]]
	}
     }
   }

}

# Affiche la transition selectionnée dans la fenetre de def d'un vecteur de synchro
proc affSynch {fenetre leTPN trans} {
global project
global currentSynch

puts "Avant $currentSynch"
    set currentSynch  [addUneSynch $currentSynch $project($leTPN,name) $trans]
puts "apres $currentSynch"
    if {$trans>0} {
      set nom "$project($leTPN,name).$trans"
    } else {
      set nom "   "
    }
       $fenetre delete synch$leTPN 
       $fenetre addtag synch$leTPN withtag [$fenetre create text [expr 155+165*($leTPN-1)] 15 -text " $nom  " -fill red4  -font {Times 12 bold} -anchor w]
#    $ou config -text "$quoi "  -background white
}

proc afficheIndiceVector {fs leTPN} {
    global tabTransition tpn leVecteur
    global project
    global fin
    global ok
    global infini
    global currentSynch


set indicet 1
    for {set i 1} {$tabTransition($leTPN,$i,statut)!=$fin} {incr i} {
	if {$tabTransition($leTPN,$i,statut)==$ok} {incr indicet} }
        

    # ++++++ le fond blanc
    $fs addtag fondBlanc$leTPN withtag  [$fs create rect [expr 105+($leTPN-1)*165] 80 [expr  245+($leTPN-1)*165] [expr 90+10*$indicet] -width 1 -fill white -outline white]

#    $c config -bg white

   $fs addtag tpnName withtag [$fs create text [expr 110+165*($leTPN-1)] 45 -text "      $project($leTPN,name) " -fill black  -font {Times 14  bold} -anchor w]

     $fs addtag legende withtag [$fs create text [expr 110+165*($leTPN-1)] 75 -text "index         Name" -fill black  -font {Times 12} -anchor w]
 

    $fs addtag trait withtag [$fs create line [expr 150+165*($leTPN-1)] 70 [expr 150+165*($leTPN-1)] [expr 90+10*$indicet] -tags item -fill black  -width 2]
$fs addtag trait2 withtag [$fs create line [expr 105+165*($leTPN-1)] 80 [expr 245+165*($leTPN-1)] 80 -tags item  -fill black  -width 2]

     $fs addtag synch$leTPN withtag [$fs create text [expr 110+165*($leTPN-1)] 15 -text "      " -fill black  -font {Times 12} -anchor w]

set indicet 1
set t t
 set transIName [$fs create text [expr 110+165*($leTPN-1)] [expr 80 + 10*$indicet] -text "  none                     "  -fill blue4  -font {Times 12} -anchor w]
      $fs addtag n$leTPN$t withtag $transIName
      $fs bind n$leTPN$t <Any-Enter> "anyEnterRed $fs"
      $fs bind n$leTPN$t <Any-Leave> "anyLeaveBlue $fs"
      $fs bind n$leTPN$t <Button-1> "affSynch $fs $leTPN 0 "

    # place par place
    for {set i 1} {$tabTransition($leTPN,$i,statut)!=$fin} {incr i} {
	if {$tabTransition($leTPN,$i,statut)==$ok} {
	    set indicet [expr $indicet+1]

      if {[zeroInfty $leTPN $i]} { 
	    set transIName [$fs create text [expr 110+165*($leTPN-1)] [expr 80 + 10*$indicet] -text " [digit4 $i]           $tabTransition($leTPN,$i,label,nom)" -fill blue4  -font {Times 12 bold} -anchor w]
      $fs addtag n$leTPN$t$i withtag $transIName
      $fs bind n$leTPN$t$i <Any-Enter> "anyEnterRed $fs"
      $fs bind n$leTPN$t$i <Any-Leave> "anyLeaveBlue $fs"
      $fs bind n$leTPN$t$i <Button-1> "affSynch $fs $leTPN $i"
      } else {
	    set transIName [$fs create text [expr 110+165*($leTPN-1)] [expr 80 + 10*$indicet] -text " [digit4 $i]           $tabTransition($leTPN,$i,label,nom)" -fill lightgray  -font {Times 12 } -anchor w]
      $fs addtag n$leTPN$t$i withtag $transIName
      }
	}
    }
}

proc digit4 {n} {
    if {$n>999} {
      return "$n"
    } elseif {$n>99} {
      return " $n"
    } elseif {$n>9} {
      return "  $n"
    } else { return "   $n"}
}


proc zeroInfty {leTPN nT} {
 global tabTransition  
 global parameters
global infini

set oui 1
 if {$parameters==0} {	
    if {!(($tabTransition($leTPN,$nT,dmin)==0)&&(($tabTransition($leTPN,$nT,dmax)==0)||($tabTransition($leTPN,$nT,dmax)==$infini)))} {
	if {$tabTransition($leTPN,$nT,dmax)==$infini} { set bomax "infty\["} else {set bomax $tabTransition($leTPN,$nT,dmax)\]}
set oui 0
 #       set button [tk_messageBox -icon error -message  "Only \[0,0\] or \[0,infty\[ transition is allowed in synchronization function. \n Here :\[$tabTransition($tpn,$nT,dmin),$bomax"] 
    }
 } else {
     if {!(((![string compare $tabTransition($leTPN,$nT,minparam) "0"])||(![string compare $tabTransition($leTPN,$nT,minparam) ""]))&&((![string compare $tabTransition($leTPN,$nT,maxparam) ""])||(![string compare $tabTransition($leTPN,$nT,maxparam) "0"])||(![string compare $tabTransition($leTPN,$nT,maxparam) "$infini"])))} {
	if {$tabTransition($leTPN,$nT,maxparam)==""} { set bomax "infty\["} else {set bomax $tabTransition($leTPN,$nT,maxparam)\]}
set oui 0
#        set button [tk_messageBox -icon error -message  "Only \[0,0\] or \[0,infty\[ transition is allowed in synchronization function. \n Here :\[$tabTransition($tpn,$nT,minparam),$bomax"] 
    }
 }
return $oui
}

proc isInSynch {listeSynch nomInstance} {
   return [lsearch -exact $listeSynch $nomInstance]
}

proc isInSynchWithoutLabel {listeGlobale unVecteur} {
# On considere une liste de liste et dans les sous liste le label de la synchro est en 0 
    puts "glob : $listeGlobale ;;; vect : $unVecteur"
 set unVecteur [lreplace $unVecteur 0 0 "rien"]
    set resul -1
    for {set i 0} {$i<[llength $listeGlobale]} {set i [expr $i+2]} {
        set extraireVecteur  [lreplace [lindex $listeGlobale $i] 0 0 "rien"]
puts "$i --> $extraireVecteur ----------------- $unVecteur gggg"
#on teste si les 2 listes sont egales
	if {[string compare $extraireVecteur $unVecteur]==0} {
puts "ben oui $i"
	   set resul $i
       }
puts "la"
    }
puts "retout $resul"
return $resul
}


proc addUneSynch {listeSynch nomInstance indT} {
    set deja [isInSynch $listeSynch $nomInstance]
    if {$deja >-1} {
        set listeSynch  [lreplace $listeSynch [expr $deja +1]  [expr $deja +1] $indT]

    } else {
      lappend listeSynch $nomInstance
      lappend listeSynch $indT
    }
    return $listeSynch
}

proc deleteUneSynch {listeSynch nomInstance} {
    for {set i 0} {$i<[llength $listeSynch]} {incr i} {
	if {[lsearch [lindex $listeSynch $i] $nomInstance] > -1} {
	    set laListe [lreplace [lindex $listeSynch $i] [lsearch [lindex $listeSynch $i] $nomInstance]  [lsearch [lindex $listeSynch $i] $nomInstance] ]
#	    if {[llength $laListe]>1} {
#		set listeSynch [lreplace $listeSynch $i [expr $i+1] $laListe]
#	    } else {
#		#supprimer synchro a un seul element ??????
#		set listeSynch [lreplace $listeSynch $i $i]
#		set i [expr $i-1]
#	    }
       }
    }
}


# si un des templates change de nom : on reecrit les vecteurs de synchronisation

proc reecrireLesSynchros {oldNameInstance newNameInstance} {
global project
global currentSynch

#si la fenetre de synchro est ouverte changer aussi dans currentSYnch
    set deja [isInSynch  $currentSynch $oldNameInstance]
    if {$deja >-1} {
              set currentSynch  [lreplace $currentSynch $deja  $deja $newNameInstance]
    }

    for {set i 0} {$i<[llength $project(liste)]} {incr i} {
         set vectSynch [lindex  $project(liste) $i]
         set deja [isInSynch  $vectSynch $oldNameInstance]
         if {$deja >-1} {
              set vectSynch  [lreplace $vectSynch $deja  $deja $newNameInstance]
	      set project(liste)  [lreplace $project(liste) $i $i  $vectSynch]
	 }
    }
   set fm .manage.global.frame.c
   effacerSyncro $fm
   afficherToutesLesSynchros $fm
}


proc effacerSyncro {fm} {
global project 

    for {set i 0} {$i<[llength $project(liste)]} {incr i} {
        set vectSynch [lindex  $project(liste) $i]
        $fm delete synch$i
    }
}

proc afficherToutesLesSynchros {fm} {
global project 

    for {set i 0} {$i<[llength $project(liste)]} {incr i} {
        set vectSynch [lindex  $project(liste) $i]
        set synchName [$fm create text 200 [expr 35 + 20*$i] -text [affUnVectSynch $vectSynch] -fill blue4  -font {Times 14} -anchor w]
        $fm addtag synch$i withtag $synchName
        $fm bind synch$i <Any-Enter> "anyEnterRed $fm"
        $fm bind synch$i <Any-Leave> "anyLeaveBlue $fm"
        $fm bind synch$i <Button-2>  "addSynchro $fm [list $vectSynch]" 
        $fm bind synch$i <Double-Button-1> "addSynchro $fm [list $vectSynch]" 

    }
}


proc ordonneVect {vecteurSynchro} {
global project 

    set listeProvisoire [list]
# d'abord le label :
    lappend listeProvisoire [lindex $vecteurSynchro 0]
# puis la synchro :
    for {set i 1} {$i <= $project(nbTPN)} {incr i} {
        set indiceInstance [isInSynch $vecteurSynchro $project($i,name)]
	if {$indiceInstance>-1} {
	    lappend listeProvisoire [lindex $vecteurSynchro $indiceInstance]
	    lappend listeProvisoire [lindex $vecteurSynchro [expr $indiceInstance+1]]
	}
    }
return $listeProvisoire
}

proc alone {vecteurSynchro} {

# alone si il y a 0 ou 2 elements dans la liste
    if {[llength $vecteurSynchro]<2} {
      return 1
    } else {
      return 0
    }
}

proc synchExisteDeja  {vecteurSynchro} {
global project 

    if {[isInSynchWithoutLabel $project(liste) $vecteurSynchro]>-1} { 
      return 1
    } else {
      return 0
    }
}
