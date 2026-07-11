# This file is part of the Rom√©o model-checking software
# 
# Copyright University of Nantes, √âcole Centrale de Nantes, IRCCyN
# 
# Contributors: Olivier H. Roux (2000 -- 2015)
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

# procedure menuHaut : creation du menu pricipale
# procedure place : creation de la fenetre d'edition du TPN
# procedures associes au menu DELETE : queCreerDetruirePTLPTF 
# procedure associe au menu Scheduler : definirProcesseur
# procedure ecrire dans la ligne du bas




#******************************* CREATION DU MENU ******************************

proc menuHaut {w c prems} {
    global cheminFichiers cheminExe
    global modif nomRdP
    global tabPlace tabTransition nbProcesseur 
    global tpn tabUnDo
    global tabFlechePT tabFlecheTP newFPT newFTP
    global deltaX deltaY maxX maxY
    global dos editAuto francais parameters synchronized typePN computOption cost
    global gpnU gpnK mercutioU mercutioK
    global choixOrdo
    global parser
    global versionRomeo
    global zoom plateforme
    global tabConstraint
    global nbConstraints
    global rienQuePourMoi
    
    # choixOrdo ne sert ‡ rien mais peut etre plus tard...
    
    global fin ok destroy
    global detruirePlace detruireTransition detruireFleche
    global creerLien creerPlace creerTransition
    global detruireNoeud creerNoeud
    global infini
    global firstTime

#    set ::menuFontSize [expr [font actual TkDefaultFont -size]+1]
#    font create menufont -family [font actual TkDefaultFont -family] -size $::menuFontSize
    option add *Menu.font menufont
 #   puts "Police par d√©faut : [font actual TkDefaultFont]"
 #   puts "Famille : [font actual TkDefaultFont -family]"
 #   puts "Taille  : [font actual TkDefaultFont -size]"
    
    # crÈation des menu
# Avec la version 8.6 de wish il n'y aura pas besoin de dÈtruire les menus mais avec la 8.5 il faut   
#    if { $firstTime(menu) == 1} {
#    	set firstTime(menu) 0
    if { $firstTime(menu) == 1} {
    	set firstTime(menu) 0
    } else {
       destroy .romeo_menu
    }
       menu .romeo_menu 
        .romeo_menu add cascade -label [mc "File"] -menu .romeo_menu.file
        menu .romeo_menu.file -tearoff 0 
        # crÈation des items du menu File
        .romeo_menu.file add command -label [mc "New"]  -command "nouveauRdP $w $c " -accelerator "Ctrl+N"
        .romeo_menu.file add command -label [mc "Open..."] -command "ouvrirOnglet $w $c" -accelerator "Ctrl+O"
        .romeo_menu.file add command -label [mc "Close"] -command "fermerOngletCourrant $w $c" -accelerator "Ctrl+F"
        .romeo_menu.file add separator
        .romeo_menu.file add command -label [mc "Save"]  -command "aiguillageEnregistrer $w" -accelerator "Ctrl+S"
        .romeo_menu.file add command -label [mc "Save as..."]  -command "enregistrerSousRdP $w" 
        .romeo_menu.file add separator
        .romeo_menu.file add command -label [mc "Export to PostScript..."]  -command "imprimer $w $c"
        .romeo_menu.file add command -label [mc "Export to LaTeX (Tikz)..."]  -command "export2tikz $c"
#        .romeo_menu.file add command -label [mc "Export to TINA..."] -command "export2tina $c" 
        #  .romeo_menu.file add command -label [mc "Export to MarkG..."] -command "export2MarkG $c 0"
        #  .romeo_menu.file add command -label [mc "Export to MarkG (untimed)..."] -command "export2MarkG $c 1"
#        .romeo_menu.file add command -label [mc "Import from TINA..."]  -command "importFromTina $c" 

           .romeo_menu.file add command -label "Export to CTS ..."  -command "exportversCTS noformula 1" 

# A commenter Version Perso 
        if {$rienQuePourMoi} {
           .romeo_menu.file add command -label "Export for all parameters values..."  -command "genererValParamXml" 
	}
    
# DESACTIVATION de OSATE 2 ROMEO        
#      if {![string compare $plateforme "windows"]} {
#        .romeo_menu.file add command -label "Import from OSATE (.AAXL)..."  -command "importFromOsate $c"
#      }  
        .romeo_menu.file add separator
        .romeo_menu.file add command -label [mc "Exit"]  -command "quitterRdP $w"
        
        # autre proposition d'organisation des menus
        # menu Èdition
         menu .romeo_menu.edit -tearoff 0
        .romeo_menu add cascade -label [mc "Edit"] -menu .romeo_menu.edit
        
        #Undo
        .romeo_menu.edit add command -label [mc "Undo"] -command "unDoModif $w" -accelerator "Ctrl+Z"
        .romeo_menu.edit add separator 
 
        #edition place
        .romeo_menu.edit add command -label [mc "Place"] -command "queCreerDetruirePTLPTF $w 1 0 0 0 0 0 0 0" -accelerator "Ctrl+P"
        
        #edition transition
        .romeo_menu.edit add command -label [mc "Transition"] -command "queCreerDetruirePTLPTF $w 0 1 0 0 0 0 0 0" -accelerator "Ctrl+T"
        
        #edition arc
        menu .romeo_menu.edit.arc -tearoff 0
        .romeo_menu.edit add cascade -label [mc "Arc..."] -menu .romeo_menu.edit.arc
        .romeo_menu.edit.arc add command -label [mc "Add"] -command "queCreerDetruirePTLPTF $w 0 0 1 0 0 0 0 0" -accelerator "Ctrl+A"
        .romeo_menu.edit.arc add command -label [mc "Delete"] -command "queCreerDetruirePTLPTF $w 0 0 0 0 0 0 1 0"
        .romeo_menu.edit.arc add command -label [mc "Reset arc"] -command "resetArcSelect $w" -accelerator "Ctrl+R"
        .romeo_menu.edit.arc add command -label [mc "Add Nail"] -command "queCreerDetruirePTLPTF $w 0 0 0 1 0 0 0 0"
        .romeo_menu.edit.arc add command -label [mc "Delete Nail"] -command "queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 1"
        
        #copier/coller/couper 
        .romeo_menu.edit add separator 
        .romeo_menu.edit add command -label [mc "Select"] -command "queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0" -accelerator "Ctrl+N"
        .romeo_menu.edit add command -label [mc "Paste selection"] -command "copierLaSelection $w" -accelerator "Ctrl+V"
        .romeo_menu.edit add command -label [mc "Delete selection"] -command "detruireLaSelection $c" -accelerator "Del"
        .romeo_menu.edit add command -label [mc "Delete"] -command "queCreerDetruirePTLPTF $w 0 0 0 0 1 1 1 1"

    .romeo_menu.edit add separator
    set message "No graphical data"
    .romeo_menu.edit add command -label "Auto Positionning" -command "fautIlPlacer 1" -accelerator "Ctrl+M"

        # SÈparateur
        .romeo_menu.edit add separator 
        # PrÈfÈrences
        .romeo_menu.edit add command -label [mc "Preferences"] -command "MAP $w $c"
                
#---------------------------- Septembre 2014 : On supprime les menus de calcul des differents graphes ------------------------------------- 
       # menu pn
#        menu .romeo_menu.pn -tearoff 0
#        .romeo_menu add cascade -label [mc "PN"] -menu .romeo_menu.pn
#        .romeo_menu.pn add command -label [mc "Marking Graph"]  -command "calculGDC 0 m"
        
	#typePN : -1 : stopwatch ;   -2 scheduling ; 1 t-tpn ; 2 p-tpn

        #menu p-tpn

#         if {($typePN==2)&&($parameters==0)} {
#	    menu .romeo_menu.ptpn -tearoff 0 
#	    .romeo_menu add cascade -label "P-TPN" -menu .romeo_menu.ptpn
#	    .romeo_menu.ptpn add command -label [mc "Zone-Based Graph"] -command "stateSpacePTPN 1"
#        }

        #menu t-tpn
#        if {($typePN==1)&&($parameters==0)} {
#	    menu .romeo_menu.tpn -tearoff 0 
#	    .romeo_menu add cascade -label "T-TPN" -menu .romeo_menu.tpn
#	    .romeo_menu.tpn add command -label [mc "State-Class Graph"] -command "calculGDC 0 g" 
#	    .romeo_menu.tpn add command -label [mc "State-Class Timed Automaton"] -command "calculGDC 0 a" 
#	    .romeo_menu.tpn add separator
#	    .romeo_menu.tpn add command -label "[mc "Zone-Based Graph"] (Inclusion)" -command "calculZBG 0 0"
#	    .romeo_menu.tpn add command -label "[mc "Zone-Based Graph"] (LTL)" -command "calculZBG l 0"
#	    .romeo_menu.tpn add command -label [mc "Marking Timed Automaton"] -command "calculZBG 0 a" 
#	    .romeo_menu.tpn add separator
#	    .romeo_menu.tpn add command -label "Unfold" -command "unfolding 0" 
#	    .romeo_menu.tpn add separator
#	    .romeo_menu.tpn add command -label [mc "Structural translation to Timed Automaton (UPPAAL format)"] -command "genererAutomateUPPAALSous"
#	    .romeo_menu.tpn add command -label [mc "Transitions/Places index"] -command "afficheCorresUPPAAL"
#	}

        # menu setpn ou stopwatches
#       if {($typePN<0)&&($parameters==0)} {
#	    menu .romeo_menu.setpn -tearoff 0
#	    .romeo_menu add cascade -label "Stopwatch-PN" -menu .romeo_menu.setpn
#	    .romeo_menu.setpn add command -label [mc "Overapproximation of Extended State-Class Graph"] -command "calculGDC d g"
#	    .romeo_menu.setpn add command -label [mc "Exact computation (polyhedral) of Extended SCG"] -command "calculGDC p g"
#	    .romeo_menu.setpn add command -label [mc "Exact computation (DBM + polyhedra) of  Extended SCG"] -command "calculGDC x g"
#	    .romeo_menu.setpn add command -label [mc "State-Class Stopwatch Automaton (-> Hytech format)"] -command "calculGDC d a"
#        }
#        # menu scheduler
#        menu .romeo_menu.scheduler -tearoff 0
#        .romeo_menu add cascade -label [mc "Scheduler"] -menu .romeo_menu.scheduler
#        .romeo_menu.scheduler add command -label [mc "Define"] -command  "definirProcesseur $c"

	# menu parametric
        if {$parameters>=1} {
	    menu .romeo_menu.paramtpn -tearoff 0
	    .romeo_menu add cascade -label "Parametric-PN" -menu .romeo_menu.paramtpn
#	    .romeo_menu.paramtpn add command -label [mc "Parametric State-Class Graph"] -command "calculGDC pp g"
	    .romeo_menu.paramtpn add command -label [mc "Constraints on parameters"] -command "additionalConstraints"
#	    .romeo_menu.paramtpn add separator
#	    .romeo_menu.paramtpn add command -label "Unfold" -command "unfolding 1" 
	    #        .romeo_menu.ptpn add separator
	}

	# menu COST
        if {$cost>0} {
	    menu .romeo_menu.costpn -tearoff 0
	    .romeo_menu add cascade -label "Cost-TPN" -menu .romeo_menu.costpn
	    .romeo_menu.costpn add command -label [mc "Timed cost"] -command "addingTimedCost"
	}

        
        #menu aide
        menu .romeo_menu.help -tearoff 0
        .romeo_menu add cascade -label [mc "Help"] -menu .romeo_menu.help
        .romeo_menu.help add command -label [mc "About..."] -command "irccyn"
#        .romeo_menu.help add command -label [mc "Licence..."]
#        .romeo_menu.help add command -label [mc "Contact..."] -command "irccyn"
        .romeo_menu.help add command -label [mc "Help"]  -font menufont -command "aide" -accelerator "Ctrl+H" 

# suppession de l'acolade qui correspond au if qui est supprimÈ	
 #   }

    # mise ‡ jour de l'Ètat des items de menu

# INUTILE DONC EN COMMENTAIRE CAR ON REFAIT LE MENU A CHAQUE FOIS QUE L ON CHANGE DE CLASSE DE MODELES
#   if { $parameters >= 1} {
#    	for {set i 1} { $i<= [.romeo_menu index end] } { incr i } {
#    		if { [.romeo_menu entrycget $i -label ] == "T-TPN" } {
#    			.romeo_menu entryconfigure $i -state disabled 
#    		}
#    		if { [ .romeo_menu entrycget $i -label ] == "P-TPN" } {
#    			.romeo_menu entryconfigure $i -state disabled
#    		}
#    		if { [.romeo_menu entrycget $i -label] == [mc "Stopwatch-PN"] } {
#    			.romeo_menu entryconfigure $i -state disabled
#    		}
#                if {   [.romeo_menu entrycget $i -label] == [mc "Parametric-PN"] } {.romeo_menu entryconfigure $i -state normal}
#    	}
#    } elseif {  $typePN == 1 } {
#	# typePN :  1 : T-TPN ;   2 P-TPN  
#
#    	# les indices changent suivant la plateforme, utilise le label pour
#    	# dÈtecter les bons items ‡ activer
#    	for {set i 1} { $i<= [.romeo_menu index end] } { incr i } {
#    		if { [.romeo_menu entrycget $i -label ] == "T-TPN" } {
#    			.romeo_menu entryconfigure $i -state active 
#    		}
#    		if { [ .romeo_menu entrycget $i -label ] == "P-TPN" } {
#    			.romeo_menu entryconfigure $i -state disabled
#    		}
#    		if { [.romeo_menu entrycget $i -label] == [mc "Stopwatch-PN"] } {
#    			.romeo_menu entryconfigure $i -state disabled 
#    		}
#                if {   [.romeo_menu entrycget $i -label] == [mc "Parametric-PN"] } {.romeo_menu entryconfigure $i -state disabled}
#    	}
#    } elseif {  $typePN == 2 } {
#	# typePN :  1 : T-TPN ;   2 P-TPN  
#    	for {set i 1} { $i<= [.romeo_menu index end] } { incr i } {
#    		if { [.romeo_menu entrycget $i -label ] == "P-TPN" } {
#    			.romeo_menu entryconfigure $i -state active 
#    		}
#    		if { [ .romeo_menu entrycget $i -label ] == "T-TPN" } {
#    			.romeo_menu entryconfigure $i -state disabled
#    		}
#    		if { [.romeo_menu entrycget $i -label] == [mc "Stopwatch-PN"] } {
#    			.romeo_menu entryconfigure $i -state disabled 
#    		}
#                if {   [.romeo_menu entrycget $i -label] == [mc "Parametric-PN"] } {.romeo_menu entryconfigure $i -state disabled}
#    	}
#    } elseif { $typePN <= -1 } {
#	# typePN :  -1 : stopwatch ;   -2 scheduling 
#    	for {set i 1} { $i<= [.romeo_menu index end] } { incr i } {
#    		if { [ .romeo_menu entrycget $i -label ] == [mc "T-TPN"] } {
#    			.romeo_menu entryconfigure $i -state disabled
#    		}
#    		if { [ .romeo_menu entrycget $i -label ] == "P-TPN" } {
#    			.romeo_menu entryconfigure $i -state disabled
#    		}
#    		if { [.romeo_menu entrycget $i -label] == [mc "Stopwatch-PN"] } {
#    			.romeo_menu entryconfigure $i -state normal
#    		}
#                if {   [.romeo_menu entrycget $i -label] == [mc "Parametric-PN"] } {.romeo_menu entryconfigure $i -state disabled}
#    	}
#    }

   if {($typePN <= -1)||($parameters>=1)} {
	for {set i 1} { $i<= [.romeo_menu.file index end] } { incr i } {
	    if {[.romeo_menu.file type $i ] == "command"} {
    		if { [.romeo_menu.file entrycget $i -label ] == [mc "Import from TINA..."] } {
   	          .romeo_menu.file entryconfigure $i -state disabled
		}
   		if { [ .romeo_menu.file entrycget $i -label ] == [mc "Export to TINA..."] } {
   	          .romeo_menu.file entryconfigure $i -state disabled
		}
	    }
	}
   } else {
	for {set i 1} { $i<= [.romeo_menu.file index end] } { incr i } {
	    if {[.romeo_menu.file type $i ] == "command"} {
    		if { [ .romeo_menu.file entrycget $i -label ] == [mc "Import from TINA..."] } {
   	          .romeo_menu.file entryconfigure $i -state normal
		}
    		if { [ .romeo_menu.file entrycget $i -label ] == [mc "Export to TINA..."] } {
   	          .romeo_menu.file entryconfigure $i -state normal
		}
            }
	}
   }

}
# fin de la procedure menuHaut

# ********************** CREATION DE LA FENETRE D'EDITION DU TPN **************************

proc procedurePlace {} {
    
    global cheminExe cheminFichiers modif nomRdP
    global tabPlace tabTransition nbProcesseur nbTokenColor
    global tpn tabUnDo 
    global tabFlechePT tabFlecheTP newFPT newFTP
    global deltaX deltaY maxX maxY
    global dos editAuto francais synchronized typePN controle
    global gpnU gpnK mercutioU mercutioK
    global quadrillage
    global zoom plateforme
    
    # Initialisation des variables booleennes globales
    global fin ok destroy
    global detruirePlace detruireTransition detruireFleche
    global creerLien creerPlace creerTransition
    global detruireNoeud creerNoeud
    global versionRomeo
    global maxX maxY
    global boutonDessin
    global firstTime
    global property


    # pour cacher la fenetre principale
    wm withdraw .

    set r .romeo
#    catch {destroy $r}


    #hack pour une vraie barre de menu :p
    toplevel $r -menu .romeo_menu 
    
    #  wm visual $r best
    wm title $r "ROMEO"
    wm iconname $r "Romeo"
    #focus -force.romeo
	wm geometry .romeo +30+55
    wm protocol $r WM_DELETE_WINDOW {quitterRdP .romeo}
    set w $r.global
    #  $w config  

    set c $w.frame.c

    frame $w
    pack $w -side left -expand yes -fill both
    #++++++++++++++ creation de la barre du haut et du menu
#    puts [winfo fpixels .romeo 2.54c]
 #   puts [winfo screen .romeo]
#        set  dpi [winfo screendepth .romeo]
#puts $dpi

    menuHaut $w $c 1


    #++++++++++++++ creation de la deuxieme barre du haut
    frame $w.barreHaut 
    pack $w.barreHaut -side top -expand 0

# TODO REMETTRE LE BOIUTON INSERT -------------------------------------------------------------------
#    button $w.barreHaut.insert -text [mc "Insert"] -command "ouvrirPointXML $w $c 1 0" 
#    pack configure $w.barreHaut.insert -side left -padx 5

#    if {[catch {package require BWidget}]} {
#    } else {
#	set boxOpen [ButtonBox $w.barreHaut.boxOpen -spacing 0 -padx 1 -pady 1]
#	$boxOpen add -image [Bitmap::get new] \
#	    -highlightthickness 0 -takefocus 0 -relief link -borderwidth 1 -padx 1 -pady 1 \
#	    -helptext [mc "Create a new net"] -command "nouveauRdP $w $c"
#	$boxOpen add -image [Bitmap::get open] \
#	    -highlightthickness 0 -takefocus 0 -relief link -borderwidth 1 -padx 1 -pady 1 \
#	    -helptext [mc "Open an existing net"] -command "ouvrirOnglet $w $c"
#	$boxOpen add -image [Bitmap::get save] \
#	    -highlightthickness 0 -takefocus 0 -relief link -borderwidth 1 -padx 1 -pady 1 \
#	    -helptext [mc "Save the net"] -command "aiguillageEnregistrer $w"
#	pack $boxOpen -side left -anchor w
#
#	set sep [Separator $w.barreHaut.sep -orient vertical]
#	pack $sep -side left -fill y -padx 4 -anchor w
 #   }
    creerBoutonsFichiers $w $c $::sizeBouton
    creerBoutonZoom $w $c $::sizeBouton

    
  
    frame $w.barreHaut.d 
    pack $w.barreHaut.d -side right -padx 5
    button $w.barreHaut.d.control -text [mc "Control Panel"] -font menufont -command "controlPanel $w $c" 
    pack configure $w.barreHaut.d.control -side right -padx 5

    button $w.barreHaut.check -text [mc "Checker"] -font menufont -command "checkProperty" 
    pack configure $w.barreHaut.check -side right -padx 5

    button $w.barreHaut.invariant -text [mc "Structural"] -font menufont -command "invariant" 
    pack configure $w.barreHaut.invariant -side right -padx 5

    button $w.barreHaut.statespace -text [mc "State Space"] -font menufont -command "stateSpace" 
    pack configure $w.barreHaut.statespace -side right -padx 5
    
    button $w.barreHaut.simulate -text "Simulator" -font menufont -command "simulateTPN $w $c" -state normal
    pack configure $w.barreHaut.simulate -side right -padx 5 

 #   if {$controle} {
#	$w.barreHaut.simulate configure -state disabled
 #   }
    button $w.barreHaut.edit -text [mc "Editor"] -font menufont -command "editTPN $w $c" -state disabled
    pack configure $w.barreHaut.edit -side right -padx 5 

   # ++++++++++++++++++++Appel au project manager +++++++++++++++++++++++++++

#    button $w.barreHaut.manage -text [mc "Project Manager"] -command "openProject" 
#    pack configure $w.barreHaut.manage -side right -padx 5


 #++++++++++++++ creation de la  barre d'onglet
    frame $w.onglet 
#    frame $w.declaration 
    pack $w.onglet -side top -expand 0 -fill x 
#    pack $w.declaration -side top -expand 0 -fill x 
 $w.onglet configure -relief sunken
    
    # ++++++++++++++++++++ Creation de la Barre de gauche graphique +++++++++++++++++++++++++++

    #[package version BWidget]
    frame $w.barreGauche 
    pack $w.barreGauche -side left -expand 0

    frame $w.barreGauche.copycut
pack $w.barreGauche.copycut -side top -expand 0


    creerBoutonCopyCut $w $c $::sizeBouton
  
    
    canvas $w.barreGauche.sep -width 20 -height 5 
    pack $w.barreGauche.sep -side top

    # ****+++++ Creation de la Barre <Place Transition arc noeud Selectionner detruire> ++++++*****

    creerBarreDessin $w $c

    # ++++++++++++++++++++ Creation de la ligne du bas +++++++++++++++++++++++++++

    frame $w.ligneDuBas 
    pack $w.ligneDuBas -side bottom -fill x 
    #-padx 10

    # +++++++++++++++ Creation du bouton ROMEO dans la ligne du bas++++++++++++++++++
 #   image create photo romeo -file [file join "img/romeo.png"]

  #  button $w.ligneDuBas.bouton-romeo -image romeo -command "irccyn" 
  #  pack configure $w.ligneDuBas.bouton-romeo -side left

    # *********
    frame $w.ligneDuBas.indication 
    pack $w.ligneDuBas.indication -side left -fill x 
    #-pady 2m

    label $w.ligneDuBas.indication.nomRdp 
    pack $w.ligneDuBas.indication.nomRdp -side left
 #   $w.ligneDuBas.indication.nomRdp config -text "TPN : $nomRdP($tpn(onglet))"

    #  button $w.ligneDuBas.message -text "Selection   Esc" -command "queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0" -state disabled 
    #  pack  $w.ligneDuBas.message -side left -expand 1


    # ++++++++++++++++ Creation du menu IRCCyN dans la ligne du bas ++++++++++++++++++

   # image create photo labo -file "img/logolabo.png"
   # button $w.ligneDuBas.bouton-irccyn -image labo -command "irccyn" 
   # pack configure $w.ligneDuBas.bouton-irccyn -side right

    # ++++++++++++++++ Creation de la fenetre d'affichage ++++++++++++++++++
    frame $w.out  
    pack $w.out -side bottom -fill x -padx 1
    #-pady 2m -padx 10

    text $w.out.texte -yscrollcommand "$w.out.vscroll set" -width 100 -height 6 -bg white -wrap word -font fontEditor
    scrollbar $w.out.vscroll -command "$w.out.texte yview"  
    pack $w.out.texte -side left -fill both -expand yes
    pack $w.out.vscroll -side right -fill y
    affiche \
"--------------------------------------------------------------------------------------------
 $versionRomeo  Copyright (c) All rights reserved                                            
                                                                                            
 LS2N (Laboratoire des Sciences du Numerique de Nantes) - UMR CNRS 6004
--------------------------------------------------------------------------------------------"

# creation du canvas et des ascenceurs ()rappel c = w.frame.c)

  canvasAsc $w $c
 slaveCanvas $w 0
    #******************Racourci commande + click sur la fenetre : creation
 if {[string compare $plateforme "windows"]} {
     event add <<Quit>> <Control-Q> <Control-q> <Command-Q> <Command-q> 
     event add <<Paste>> <Control-V> <Control-v> <Command-V> <Command-v>
     event add <<Save>> <Control-S> <Control-s> <Command-S> <Command-s>
     event add <<Open>> <Control-O> <Control-o> <Command-O> <Command-o>
     event add <<New>> <Control-N> <Control-n> <Command-N> <Command-n>
     event add <<AddP>> <Control-P> <Control-p>
 } else {
     event add <<Quit>> <Control-Q> <Control-q> 
     event add <<Paste>> <Control-V> <Control-v> 
     event add <<Save>> <Control-S> <Control-s> 
     event add <<Open>> <Control-O> <Control-o> 
     event add <<New>> <Control-N> <Control-n> 
     event add <<AddP>> <Control-P> <Control-p>
 }   
  event add <<AddT>> <Control-T> <Control-t>
  event add <<AddA>> <Control-A> <Control-a>
  event add <<AddR>> <Control-R> <Control-r>
  event add <<undo>> <Control-Z> <Control-z> <Command-Z> <Command-z>
  event add <<Suppr>> <BackSpace> <Delete>
  event add <<Echap>> <Escape>

 
  bind .romeo <<Quit>> "quitterRdP $w"
  bind .romeo <<Paste>> "copierLaSelection $w"
  bind .romeo <<AddP>> "queCreerDetruirePTLPTF $w 1 0 0 0 0 0 0 0"
  bind .romeo <<AddT>> "queCreerDetruirePTLPTF $w 0 1 0 0 0 0 0 0"
  bind .romeo <<AddR>> "queCreerDetruirePTLPTF $w 0 0 2 0 0 0 0 0"
  bind .romeo <<AddA>> "queCreerDetruirePTLPTF $w 0 0 1 0 0 0 0 0"
  bind .romeo <<Save>> "aiguillageEnregistrer $w"
  bind .romeo <<Open>> "ouvrirOnglet $w $c"
  bind .romeo <<New>> "nouveauRdP $w $c"
  bind .romeo <<Suppr>> "detruireLaSelection $c"
  bind .romeo <<Echap>> "escapeBarreDessin $w"
  bind .romeo <<undo>> "unDoModif $w"

#  bind $w <B3-MouseWheel> "puts "
  bind $w <Up> "$c yview scroll -3 units"
  bind $w <Down> "$c yview scroll +3 units"
  bind $w <Left> "$c xview scroll -3 units"
  bind $w <Right> "$c xview scroll +3 units"

    
# Pour Windows/Linux : molette + Shift
bind $c <MouseWheel> {
    if {[string match *Shift* %s]} {
        if {%D > 0} {
            %W yview scroll -3 units
        } else {
            %W yview scroll +3 units
        }
    }
}

# Pour X11/macOS : molette (Button-4/5) + Shift
bind $c <Shift-Button-4> {%W yview scroll -3 units}
bind $c <Shift-Button-5> {%W yview scroll +3 units}

# event add  <<scroll>> <Up>

#  bind $c <MouseWheel> "puts $nomRdP" 
# event add  <<scroll>> <MouseWheel-2>

# peut etre a mettre dans l'initialisation :
  set plot(lastX) 0
  set plot(lastY) 0
  
  load_LastOpenFile $w $c
}

#fin de la procedure place


#******************************************************************
# ++++++ le fond quadrill

proc grille c {
    global maxX maxY zoom quadrillage

    if $quadrillage {
	for {set i 1} {$i<$maxX} {set i [expr $i+30]} {
	    $c create line $i 00 $i $maxY -width 1 -fill gray
	}
	for {set i 1} {$i<$maxY} {set i [expr $i+30]} {
	    $c create line 00 $i $maxX $i -width 1 -fill gray
	}
	$c create line 0 $maxY $maxX $maxY -width 2 -fill blue
	$c create line $maxX 0 $maxX $maxY -width 2 -fill blue
    } 
}


proc basculeGrille c {
    global quadrillage

    if $quadrillage { 
	set quadrillage 0
    } else {
	set quadrillage 1
    }
    redessinerRdP $c 
} 
#******************************************************************

proc resetArcSelect {w} {
global allowedArc
 if {$allowedArc(reset)} {  
   queCreerDetruirePTLPTF $w 0 0 2 0 0 0 0 0 
 } elseif {$allowedArc(read)} {  
   queCreerDetruirePTLPTF $w 0 0 3 0 0 0 0 0 
 } elseif {$allowedArc(logicInhibitor)} {  
   queCreerDetruirePTLPTF $w 0 0 4 0 0 0 0 0 
 } elseif {$allowedArc(timedInhibitor)} {  
   queCreerDetruirePTLPTF $w 0 0 5 0 0 0 0 0 
 } else {
   queCreerDetruirePTLPTF $w 0 0 1 0 0 0 0 0 
 }
} 

#******** MISE a JOUR du nombre de processeur ***************

proc definirProcesseur {r} {
    global nb
    global nbProcesseur typePN
    global tpn tabUnDo
    global francais
    global choixOrdo
    global modif
    
    set f .fenetreProcesseur
    catch {destroy $f}
    toplevel $f
    wm title $f [mc "Scheduling extension"]
    
    set choixOrdo 0
    
    frame $f.scheduler -relief ridge -bd 2 -height 2
    label $f.scheduler.commentaire
    radiobutton $f.scheduler.priority -text [mc "Preemptive Scheduling \n based on static priority"]  -variable choixOrdo  -font menufont -relief flat  -value 0  -width 20 -anchor w
    
    pack $f.scheduler.priority -side top -pady 2 -anchor w -fill x
    pack $f.scheduler -side top -fill x

    set nb $nbProcesseur($tpn(courant))
    frame $f.nbProc -relief ridge -bd 2 -height 2
    entry $f.nbProc.saisienbProc -justify left -textvariable nb -relief sunken -width 5 -bg white
    label $f.nbProc.label
    label $f.nbProc.titre
    pack $f.nbProc.titre -side top
    pack $f.nbProc.label -side left
    pack $f.nbProc.saisienbProc -side left
    $f.nbProc.label config -text [mc "Number of CPU: "]
    $f.nbProc.titre config -text [mc "Hardware Architecture"]

    pack $f.nbProc -side top -fill x
    bind $f <Return> "validerProc $r $f"
    frame $f.buttons
    pack $f.buttons -side bottom -fill x -pady 2m
    button $f.buttons.annuler -text [mc "Cancel"] -font menufont -command  "destroy $f"
    button $f.buttons.accepter -default active -text [mc "Ok"] -font menufont -command "validerProc $r $f"
    pack $f.buttons.annuler $f.buttons.accepter  -side left -expand 1

    # ++++++ procedure interne ‡ la procedure definriProcesseur

    proc validerProc {c fl} {
	global nb
	global nbProcesseur
	global modif 
	global tpn tabUnDo


	modifTPN $tpn(courant)
	set x [format %d $nb]

	if {$nb >= 0} {
	    if {$nb>10} {set nb 10}
	    set pourTest $nbProcesseur($tpn(courant))
	    set nbProcesseur($tpn(courant)) $nb
	    destroy $fl
	    if {$nb < $pourTest}  {  redessinerRdP $c }
	} else {
	    set button [tk_messageBox -message [mc "Error: number of CPU < 0"]]
	}
    }
    # fin de la procedure definirProcesseur
}


#******** MISE a JOUR DES BOOLEENS DE DESTRUCTION ***************


proc queCreerDetruirePTLPTF {r cP cT cL cN dP dT dF dN} {

    global detruirePlace
    global detruireTransition
    global detruireFleche
    global creerLien
    global creerPlace eclair
    global creerTransition
    global detruireNoeud
    global creerNoeud
    global select
    global boutonDessin
    global allowedArc typePN


    if {$cP + $cT + $cL + $cN != 0} {
	set select(vide) 1
	set select(listePlace) [list]
	set select(listeLabelPlace) [list]
	set select(listeTransition) [list]
	set select(listeLabelTransition) [list]
	set select(listeNoeud) [list]

	if {$cP+ $cT + $cL <-3} {
	    afficheBarreDessin $r 2
	    set eclair(place) -1
	    set eclair(transition) -1
	}
	if {$cP==1} {afficheBarreDessin $r 3}
	if {$cP==2} {afficheBarreDessin $r 4}
	if {$cT>0} {afficheBarreDessin $r 5}
	if {$cL==1} {afficheBarreDessin $r 6}
	if {$cN} {afficheBarreDessin $r 7}
	if {$cL==2} {afficheBarreDessin $r 8}
	if {$cL==3} {afficheBarreDessin $r [expr 8 + $allowedArc(reset)]}
	if {$cL==4} {afficheBarreDessin $r [expr 8 + $allowedArc(reset)+ $allowedArc(read)]}
        if {$cL==5} {afficheBarreDessin $r [expr 8 + $allowedArc(reset)+ $allowedArc(read)+$allowedArc(logicInhibitor)]}
#	Preparation pour le prochain arc : if {$cL==6} {afficheBarreDessin $r [expr 7 + $allowedArc(reset)+ $allowedArc(read)+$allowedArc(logicInhibitor)+$allowedArc(timedInhibitor)]}

    } elseif {$dP + $dT + $dF + $dN ==0} {
	afficheBarreDessin $r 0
    } else {afficheBarreDessin $r 1}

    set creerPlace $cP
    set creerTransition $cT
    set creerLien $cL
    set creerNoeud $cN

    set detruirePlace $dP
    set detruireTransition $dT
    set detruireFleche $dF
    set detruireNoeud $dN

#    redessinerProjet $r
}


# ***********procedure ecrire dans la ligne du bas

proc ecrire {w unTruc} {
    label $w.ligneDuBas.indication.delta
    pack $w.ligneDuBas.indication.delta -side right
    $w.ligneDuBas.indication.delta config -text "$unTruc"
}


proc afficheBarreDessin {w nBouton} {
    global boutonDessin
    for {set i 0} {$i<12}  {incr i} {
	if {$i==$nBouton} {
	    $w.barreGauche.p itemconfig boutonDessin($i) -outline black -fill gray
	} else {
	    $w.barreGauche.p itemconfig boutonDessin($i) -outline gray -fill gray95
	}
    }
}



proc creerBoutonsFichiers  {w c size} {
    # --- Supprimer anciens boutons et s√©parateur si existants ---
    foreach b {nouveauCanvas ouvrirCanvas enregistrerCanvas sep} {
        if {[winfo exists $w.barreHaut.$b]} {
            destroy $w.barreHaut.$b
        }
    }

    # --- Bouton Nouveau (feuille avec coin pli√©) ---
canvas $w.barreHaut.nouveauCanvas -width $size -height $size \
    -bg white -highlightthickness 1 -relief raised

# Marges
set m 6
set right [expr {$size - $m}]
set bottom [expr {$size - $m}]
set foldSize [expr {$size / 4}]   ;# taille du coin pli√©

# Rectangle principal de la feuille
$w.barreHaut.nouveauCanvas create rectangle $m $m $right $bottom \
    -width 2 -outline black -fill white

# Coin pli√© (triangle)
set x1 [expr {$right - $foldSize}]
set y1 $m
set x2 $right
set y2 [expr {$m + $foldSize}]

$w.barreHaut.nouveauCanvas create polygon \
    $x1 $m   $right $m   $right $y2 \
    -fill #e0e0e0 -outline black -width 1

# Ligne de pli pour accentuer l‚Äôeffet du coin
$w.barreHaut.nouveauCanvas create line $x1 $m $right $y2 -fill grey

bind $w.barreHaut.nouveauCanvas <Button-1> [list nouveauRdP $w $c]
pack $w.barreHaut.nouveauCanvas -side left -padx 1 -pady 1


# --- Bouton Ouvrir (dossier ouvert avec fl√®che) ---
canvas $w.barreHaut.ouvrirCanvas -width $size -height $size \
    -bg white -highlightthickness 1 -relief raised

# Marges
set m 6
set top 4
set right  [expr {$size - $m}]
set bottom [expr {$size - $m}]
set midY   [expr {$size * 0.55}]   ;# hauteur du dossier

# Taille du couvercle du dossier
set tabHeight [expr {$size * 0.30}]
set tabWidth  [expr {$size * 0.55}]

# --- PARTIE DOSSIER ---

# Corps du dossier
$w.barreHaut.ouvrirCanvas create rectangle \
    $m $bottom  [expr {$m + $tabWidth}] [expr {$tabHeight}]  \
    -fill #f5e3b2 -outline black -width 2

# Couvercle du dossier (inclin√©)
$w.barreHaut.ouvrirCanvas create polygon \
    $m $bottom \
    [expr {$m + $size*0.2}] [expr {$tabHeight+ $size*0.2}] \
    [expr {$m + $tabWidth+ $size*0.2}] [expr {$tabHeight+ $size*0.2}] \
    [expr {$m + $tabWidth}] $bottom \
    -fill #f2d18b -outline black -width 2



# --- PARTIE FL√àCHE (action d‚Äôouverture) ---

# Ligne principale de la fl√®che
set arrowY [expr {$midY - $tabHeight/2}]
$w.barreHaut.ouvrirCanvas create line \
    [expr {$tabWidth+$m}]  [expr $top/2] \
    [expr {$size}] [expr {$top+$size*0.3}] \
    -width 1 -fill blue  -arrow last

# Pointe de la fl√®che
#$w.barreHaut.ouvrirCanvas create polygon \
#    [expr {$right - 6}] [expr {$arrowY - 6}] \
#    [expr {$right - 6}] [expr {$arrowY + 6}] \
#    [expr {$right + 4}] $arrowY \
#    -fill blue -outline blue

bind $w.barreHaut.ouvrirCanvas <Button-1> [list ouvrirOnglet $w $c]
pack $w.barreHaut.ouvrirCanvas -side left -padx 1 -pady 1

    # --- Bouton Enregistrer (symbole disquette) ---
    canvas $w.barreHaut.enregistrerCanvas -width $size -height $size \
        -bg white -highlightthickness 1 -relief raised
    set left 6
    set top 6
    set right [expr {$size-6}]
    set bottom [expr {$size-6}]
    $w.barreHaut.enregistrerCanvas create rectangle $left $top $right $bottom -width 2 -outline black -fill lightgrey
    $w.barreHaut.enregistrerCanvas create rectangle [expr {$left+4}] [expr {$top+4}] [expr {$right-4}] [expr {$top+($bottom-$top)/2}] \
        -width 1 -outline black -fill darkgrey
    $w.barreHaut.enregistrerCanvas create rectangle [expr {$left+4}] [expr {$top+($bottom-$top)/2 +2}] [expr {$right-4}] [expr {$bottom-4}] \
        -width 1 -outline black -fill white
    bind $w.barreHaut.enregistrerCanvas <Button-1> [list aiguillageEnregistrer $w]
    pack $w.barreHaut.enregistrerCanvas -side left -padx 1 -pady 1

    # --- S√©parateur vertical ---
    frame $w.barreHaut.sep -width 2 -bg grey
    pack $w.barreHaut.sep -side left -fill y -padx 4
}


 proc creerBoutonZoom {w c size} {
    # Taille du bouton en pixels
  if {[winfo exists $w.barreHaut.zplusCanvas]} {
        destroy $w.barreHaut.zplusCanvas
    }
    if {[winfo exists $w.barreHaut.zmoinsCanvas]} {
        destroy $w.barreHaut.zmoinsCanvas
    }
    if {[winfo exists $w.barreHaut.grid]} {
        destroy $w.barreHaut.grid
    }
  
    # --- Bouton Zoom In (canvas vectoriel) ---
    canvas $w.barreHaut.zplusCanvas -width $size -height $size \
        -bg white -highlightthickness 1 -relief raised
    $w.barreHaut.zplusCanvas create line [expr {$size/2}] 6 [expr {$size/2}] [expr {$size-6}] \
        -width 4 -fill black
    $w.barreHaut.zplusCanvas create line 6 [expr {$size/2}] [expr {$size-6}] [expr {$size/2}] \
        -width 4 -fill black
    bind $w.barreHaut.zplusCanvas <Button-1> [list zoomPlus $w $c]
    pack $w.barreHaut.zplusCanvas -side left -padx 5 -pady 5

    # --- Bouton Zoom Out (canvas vectoriel) ---
    canvas $w.barreHaut.zmoinsCanvas -width $size -height $size \
        -bg white -highlightthickness 1 -relief raised
    $w.barreHaut.zmoinsCanvas create line 6 [expr {$size/2}] [expr {$size-6}] [expr {$size/2}] \
        -width 4 -fill black
    bind $w.barreHaut.zmoinsCanvas <Button-1> [list zoomMoins $w $c]
    pack $w.barreHaut.zmoinsCanvas -side left -padx 5 -pady 5


canvas $w.barreHaut.grid -width [expr $size] -height [expr $size] -bg white
    pack $w.barreHaut.grid -side left
    set motifBouton [$w.barreHaut.grid create rect 2 2 $size $size -width 1 -outline white \
			 -fill white]
    $w.barreHaut.grid addtag boutonDessin withtag $motifBouton
    $w.barreHaut.grid bind boutonDessin <Button-1> "basculeGrille $c"
    
for {set i 2} {$i<[expr $size-1]} {set i [expr $i+int($size/4)]} {
	set ligneH($i) [$w.barreHaut.grid create line $i 4 $i [expr $size-1] -width 1 -fill gray40]     
	set ligneV($i) [$w.barreHaut.grid create line 4 $i [expr $size-1] $i -width 1 -fill gray40]
	$w.barreHaut.grid addtag lh($i) withtag $ligneH($i)
	$w.barreHaut.grid addtag lv($i) withtag $ligneV($i)
	$w.barreHaut.grid bind lh($i) <Button-1> "basculeGrille $c"
	$w.barreHaut.grid bind lv($i) <Button-1> "basculeGrille $c"
    }



}


 proc creerBoutonCopyCut {w c size} {

 if {[winfo exists $w.barreGauche.copycut.cutCanvas]} {
        destroy $w.barreGauche.copycut.cutCanvas
    }
 if {[winfo exists $w.barreGauche.copycut.copyCanvas]} {
        destroy $w.barreGauche.copycut.copyCanvas
    }
#   scaleBarreGaucheCopyCutDynamic $w 1
#    if {[catch {package require BWidget}]} {
#	button $w.barreGauche.copycut.paste -text [mc "Paste"] -command "copierLaSelection $w" 
#	pack  $w.barreGauche.copycut.paste -side top -expand 0
#	button $w.barreGauche.copycut.cut -text [mc "Delete"] -command "detruireLaSelection $c" 
#	pack  $w.barreGauche.copycut.cut -side top -expand 0

#    } else {
#	set boxPaste [ButtonBox $w.barreGauche.copycut.paste -spacing 0 -padx 1 -pady 1]
#	set boxCut [ButtonBox $w.barreGauche.copycut.cut -spacing 0 -padx 1 -pady 1]
#
#	$boxCut add -image [Bitmap::get cut] \
#	    -highlightthickness 0 -takefocus 0 -relief link -borderwidth 1 -padx 4 -pady 1 \
#	    -helptext "Cut selection"] -command "detruireLaSelection $c"
#	$boxPaste add -image [Bitmap::get paste] \
#	    -highlightthickness 0 -takefocus 1 -relief link -borderwidth 1 -padx 1 -pady 1 \
#	    -helptext "Paste selection" -command "copierLaSelection $w"
#
#	pack $boxCut -side top
#	pack $boxPaste -side top
	#button $w.barreGauche.b1 -bitmap [Bitmap::get paste]
 #   }



    
# --- Bouton Cut (ciseaux inclin√©s et ouverts) ---
canvas $w.barreGauche.copycut.cutCanvas -width $size -height $size \
    -bg white -highlightthickness 1 -relief raised

# Centre
set cx [expr {$size/2}]
set cy [expr {$size/2}]

# Proportions
 # anneaux
set r    [expr {$size * 0.12}]
 # longueur lames
set la   [expr {$size * 0.42}]
 # inclinaison
set tilt [expr {$size * 0.18}]   

# --- Anneau haut-gauche ---
 $w.barreGauche.copycut.cutCanvas create oval \
    [expr {$cx - $tilt - $r}] [expr {$cy - $tilt - $r}] \
    [expr {$cx - $tilt + $r}] [expr {$cy - $tilt + $r}] \
    -width 2 -outline black -fill white

# --- Anneau bas-gauche ---
 $w.barreGauche.copycut.cutCanvas create oval \
    [expr {$cx - $tilt - $r}] [expr {$cy + $tilt - $r}] \
    [expr {$cx - $tilt + $r}] [expr {$cy + $tilt + $r}] \
    -width 2 -outline black -fill white

# --- Lame sup√©rieure (vers haut-droite) ---
 $w.barreGauche.copycut.cutCanvas create line \
    [expr {$cx - $tilt/2}] [expr {$cy - $tilt/2}] \
    [expr {$cx + $la}]     [expr {$cy - $la/3}] \
    -width 3 -fill black -capstyle round

# --- Lame inf√©rieure (vers bas-droite) ---
 $w.barreGauche.copycut.cutCanvas create line \
    [expr {$cx - $tilt/2}] [expr {$cy + $tilt/2}] \
    [expr {$cx + $la}]     [expr {$cy + $la/3}] \
    -width 3 -fill black -capstyle round

# --- Axe central ---
 $w.barreGauche.copycut.cutCanvas create oval \
    [expr {$cx - 4}] [expr {$cy - 4}] \
    [expr {$cx + 4}] [expr {$cy + 4}] \
    -fill black -outline black

bind  $w.barreGauche.copycut.cutCanvas <Button-1> [list detruireLaSelection $c]
pack  $w.barreGauche.copycut.cutCanvas -side top -padx 5 -pady 5

# ===========================================
    #      BOUTON COPY  (deux feuilles)
    # ===========================================
    canvas $w.barreGauche.copycut.copyCanvas -width $size -height $size \
        -bg white -highlightthickness 1 -relief raised

    set marge [expr {$size * 0.15}]      ;# marge autour de la grande feuille
    set dec   [expr {$size * 0.13}]      ;# d√©calage pour la petite feuille

    # Petite feuille (derri√®re)
    $w.barreGauche.copycut.copyCanvas create rectangle \
        [expr {$marge + $dec}] [expr {$marge}] \
        [expr {$size - $marge + $dec}] [expr {$size - $marge}] \
        -outline gray40 -width 2 -fill white

    # Grande feuille (devant)
    $w.barreGauche.copycut.copyCanvas create rectangle \
        $marge [expr {$marge + $dec}] \
        [expr {$size - $marge}] [expr {$size - $marge + $dec}] \
        -outline black -width 2 -fill white

    # Lignes "texte" sur la grande feuille
    set y1 [expr {$marge + $dec + $size*0.15}]
    set y2 [expr {$y1 + $size*0.12}]
    set y3 [expr {$y2 + $size*0.12}]

    foreach y [list $y1 $y2 $y3] {
        $w.barreGauche.copycut.copyCanvas create line \
            [expr {$marge + $size*0.08}] $y \
            [expr {$size - $marge - $size*0.08}] $y \
            -width 2 -fill black
    }

    bind $w.barreGauche.copycut.copyCanvas <Button-1> [list copierLaSelection $w]
    pack $w.barreGauche.copycut.copyCanvas -side top -pady 5


}

proc zoomPlus {w c} {
    global zoom viewOnglet
    global tpn

    set zoom $viewOnglet(zoom,$tpn(onglet))
    # pour zoomer vers le milieu :
    # coef de grossissement k =1.5. Glissement =(k-1)/2k

    set deltaX [expr (5*[lindex [$c xview] 0]+[lindex [$c xview] 1])/6]
    set deltaY [expr (5*[lindex [$c yview] 0]+[lindex [$c yview] 1])/6]

    if {$zoom<5} {
	set viewOnglet(zoom,$tpn(onglet)) [expr $zoom*1.5]
	MAJdessinsProjetcourant $w
#	$c xview moveto $deltaX
#	$c yview moveto $deltaY 
    }
}

proc zoomMoins {w c} {
    global zoom viewOnglet
    global tpn maxX maxY

    set zoom $viewOnglet(zoom,$tpn(onglet))
    # pour dezoomer ‡ partir du milieu :
    # Glissement du point en haut ‡ gauche : (k-1)/4

    set deltaX [max 0 [expr (5*[lindex [$c xview] 0]-[lindex [$c xview] 1])/4]]
    set deltaY [max 0 [expr (5*[lindex [$c yview] 0]-[lindex [$c yview] 1])/4]]

    if {$zoom>0.2} {
	set viewOnglet(zoom,$tpn(onglet)) [expr $zoom/1.5]
	MAJdessinsProjetcourant $w
	
#	$c xview moveto $deltaX
#	$c yview moveto $deltaY
    }
}

proc creerBarreDessin {w c} {
    global allowedArc typePN
    global dejaHelp
    
       set dejaHelp -1      

    
    set ::haut [expr 178+27 + $allowedArc(reset)*23 + $allowedArc(read)*23 + $allowedArc(logicInhibitor)*23+$allowedArc(timedInhibitor)*23]
    canvas $w.barreGauche.p -width 21 -height $::haut -relief sunken -borderwidth 2 -bg white
    pack $w.barreGauche.p -side top


# associate all entries of menu .m.file to variable varinfo
# then declare entries of .m.file
    for {set i 0} {$i<9}  {incr i} {
	  set motifBouton [$w.barreGauche.p create rect 1 [expr 25*$i+2] 25 [expr 25*($i+1)] -outline gray \
			     -fill gray95]
	  $w.barreGauche.p addtag boutonDessin($i) withtag $motifBouton
    }

# select et del sont plus loin
 set i 3

    set motifPlace [$w.barreGauche.p create oval 6 [expr 25*$i+6] 20 [expr 25*$i+20] -width 1 -outline black -state normal \
			-fill SkyBlue2]

    incr i
    set motifToken [$w.barreGauche.p create oval 12 [expr 25*$i+12] 16 [expr 25*$i+16] -width 1 -outline black -state normal \
			-fill black]
    incr i
    set motifTransition [$w.barreGauche.p create rect 7 [expr 25*$i+10] 19 [expr 25*$i+16] -width 1 -outline black \
			     -fill yellow]

    incr i

    set motifArc [$w.barreGauche.p create line 5 [expr 25*$i+4] 18 [expr 25*$i+21]  -arrow last -fill black]

    incr i
    set motifArcNoeud [$w.barreGauche.p create line 5 [expr 25*$i+9] 12 [expr 25*$i+15] 20 [expr 25*$i+19] -fill black]
    set motifNoeud [$w.barreGauche.p create rect 10 [expr 25*$i+13] 14 [expr 25*$i+17] -width 1 -outline black -fill green]

    $w.barreGauche.p addtag motif(Place) withtag $motifPlace
    $w.barreGauche.p addtag motif(Token) withtag $motifToken
    $w.barreGauche.p addtag motif(Transition) withtag $motifTransition
    $w.barreGauche.p addtag motif(Arc) withtag $motifArc
    $w.barreGauche.p addtag motif(ArcNoeud) withtag $motifArcNoeud
    $w.barreGauche.p addtag motif(Noeud) withtag $motifNoeud

  

    incr i
    
    if {$allowedArc(reset)==1} {
  	   set motifBouton [$w.barreGauche.p create rect 1 [expr 25*$i+2] 25 [expr 25*($i+1)] -outline gray \
			     -fill gray95]
	    $w.barreGauche.p addtag boutonDessin($i) withtag $motifBouton

	    set xb 16
	    set yb [expr 25*$i+14]
	    set xa 6
	    set ya [expr 25*$i+4]
	    set motifFlush [$w.barreGauche.p create polygon [expr $xb + 3] $yb \
			[expr $xb ] [expr $yb + 3] [expr $xb + 3] [expr $yb + 6] \
			[expr $xb + 6] [expr $yb + 3] -width 1 -outline black -fill black]  
	    set motifArcFlush [$w.barreGauche.p create line $xa $ya [expr $xb + 3] [expr $yb + 3] -tags item -fill black]
	    $w.barreGauche.p addtag motif(flush) withtag $motifFlush   
	    $w.barreGauche.p addtag motif(arcFlush) withtag $motifArcFlush   
            $w.barreGauche.p bind boutonDessin($i) <Button-1> "queCreerDetruirePTLPTF $w 0 0 2 0 0 0 0 0"
            $w.barreGauche.p bind motif(flush) <Button-1> "queCreerDetruirePTLPTF $w 0 0 2 0 0 0 0 0"
            $w.barreGauche.p bind motif(arcFlush) <Button-1> "queCreerDetruirePTLPTF $w 0 0 2 0 0 0 0 0"
 	    $w.barreGauche.p bind boutonDessin($i) <Any-Enter> "afficheHelp %x %y $w $i reset-arc"

	    incr i
    }
    
    if {$allowedArc(read)==1} {
  	   set motifBouton [$w.barreGauche.p create rect 1 [expr 25*$i+2] 25 [expr 25*($i+1)] -outline gray \
			     -fill gray95]
	    $w.barreGauche.p addtag boutonDessin($i) withtag $motifBouton

	    set xb 16
	    set yb [expr 25*$i+14]
	    set xa 6
	    set ya [expr 25*$i+4]
	    set motifArcRead [$w.barreGauche.p create line $xa $ya [expr $xb + 3] [expr $yb+3] -tags item -fill black]
#	    set motifRead [$w.barreGauche.p create polygon [expr $xb + 3] $yb \
#			$xb [expr $yb + 3] [expr $xb + 3] [expr $yb + 6] \
#			[expr $xb + 6] [expr $yb + 3] -width 1 -outline black -fill lightgray]  
	    set motifRead [$w.barreGauche.p create polygon [expr $xb] $yb \
			[expr $xb+6] [expr $yb] [expr $xb +6] [expr $yb + 6] \
			[expr $xb] [expr $yb + 6] -width 1 -outline black -fill lightgray]  
	    $w.barreGauche.p addtag motif(read) withtag $motifRead   
	    $w.barreGauche.p addtag motif(arcRead) withtag $motifArcRead   
            $w.barreGauche.p bind boutonDessin($i) <Button-1> "queCreerDetruirePTLPTF $w 0 0 3 0 0 0 0 0"
            $w.barreGauche.p bind motif(arcRead) <Button-1> "queCreerDetruirePTLPTF $w 0 0 3 0 0 0 0 0"
            $w.barreGauche.p bind motif(read) <Button-1> "queCreerDetruirePTLPTF $w 0 0 3 0 0 0 0 0"
	    $w.barreGauche.p bind boutonDessin($i) <Any-Enter> "afficheHelp %x %y $w $i [mc read-arc]"
	    incr i
    }

    if {$allowedArc(logicInhibitor)==1} {
  	   set motifBouton [$w.barreGauche.p create rect 1 [expr 25*$i+2] 25 [expr 25*($i+1)] -outline gray \
			     -fill gray95]
	    $w.barreGauche.p addtag boutonDessin($i) withtag $motifBouton

	    set xb  16
	    set yb  [expr 25*$i+14]
	    set xa 6
	    set ya  [expr 25*$i+4]  
	    set motifLogicInh [$w.barreGauche.p create oval [expr $xb] [expr $yb] \
			[expr $xb + 6] [expr $yb + 6] -width .5 -outline black -fill orange]  
	    set motifArcLogicInh [$w.barreGauche.p create line $xa $ya [expr $xb] [expr $yb] -tags item -fill black]
	    $w.barreGauche.p addtag motif(logicInh) withtag $motifLogicInh   
	    $w.barreGauche.p addtag motif(arcLogicInh) withtag $motifArcLogicInh   

 	    $w.barreGauche.p bind boutonDessin($i) <Any-Enter> "afficheHelp %x %y $w $i [mc logical-inhibitor-arc]"

            $w.barreGauche.p bind boutonDessin($i) <Button-1> "queCreerDetruirePTLPTF $w 0 0 4 0 0 0 0 0"
            $w.barreGauche.p bind motif(logicInh) <Button-1> "queCreerDetruirePTLPTF $w 0 0 4 0 0 0 0 0"
            $w.barreGauche.p bind motif(arcLogicInh) <Button-1> "queCreerDetruirePTLPTF $w 0 0 4 0 0 0 0 0"
	    incr i
    }
    
    if {$allowedArc(timedInhibitor)==1} {
  	   set motifBouton [$w.barreGauche.p create rect 1 [expr 25*$i+2] 25 [expr 25*($i+1)] -outline gray \
			     -fill gray95]
	    $w.barreGauche.p addtag boutonDessin($i) withtag $motifBouton

	    set xb 16
	    set yb [expr 25*$i+14]
	    set xa 6
	    set ya [expr 25*$i+4]  
	    set motifTimedInh [$w.barreGauche.p create oval [expr $xb] [expr $yb] \
			[expr $xb + 6] [expr $yb + 6] -width 2 -outline black -fill white]  
	    set motifArcTimedInh [$w.barreGauche.p create line $xa $ya [expr $xb] [expr $yb] -tags item -fill black]
	    $w.barreGauche.p addtag motif(timedInh) withtag $motifTimedInh   
	    $w.barreGauche.p addtag motif(arcTimedInh) withtag $motifArcTimedInh   

 	    $w.barreGauche.p bind boutonDessin($i) <Any-Enter> "afficheHelp %x %y $w $i [mc timed-inhibitor-arc]"

        $w.barreGauche.p bind boutonDessin($i) <Button-1> "queCreerDetruirePTLPTF $w 0 0 5 0 0 0 0 0"
        $w.barreGauche.p bind motif(timedInh) <Button-1> "queCreerDetruirePTLPTF $w 0 0 5 0 0 0 0 0"
        $w.barreGauche.p bind motif(arcTimedInh) <Button-1> "queCreerDetruirePTLPTF $w 0 0 5 0 0 0 0 0"
	    incr i
    }

    # et selectionner detruire eclair :

    set motifSelect [$w.barreGauche.p create rect 7 7 22 22  -dash 3 -width 1 -outline black ]
    set motifDel1 [$w.barreGauche.p create line 5 30 20 45 -width 5 -fill red ]
    set motifDel2 [$w.barreGauche.p create line 5 45 20 30  -width 5 -fill red ]
    set motifEclair [$w.barreGauche.p create line 5 72 12 60 16 68 24 55 -width 1 -arrow last -fill blue ]
    set motifEclairP [$w.barreGauche.p create oval 5 73 11 67 -width 1 -outline black -state normal \
			-fill SkyBlue2]
    set motifEclairT [$w.barreGauche.p create rect 7 61 15 58 -width 1 -outline black \
			     -fill yellow]


    $w.barreGauche.p addtag motif(Select) withtag $motifSelect
    $w.barreGauche.p addtag motif(Del1) withtag $motifDel1
    $w.barreGauche.p addtag motif(Del2) withtag $motifDel2
    $w.barreGauche.p addtag motif(Eclair) withtag $motifEclair
    $w.barreGauche.p addtag motif(Eclair) withtag $motifEclairP
    $w.barreGauche.p addtag motif(Eclair) withtag $motifEclairT

    $w.barreGauche.p bind boutonDessin(0) <Button-1> "queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0"
    $w.barreGauche.p bind boutonDessin(1) <Button-1> "queCreerDetruirePTLPTF $w 0 0 0 0 1 1 1 1"

    $w.barreGauche.p bind motif(Eclair) <Button-1> "queCreerDetruirePTLPTF $w -2 -1 -1 0 0 0 0 0"
    $w.barreGauche.p bind motif(Eclair) <Any-Enter>  "afficheHelp %x %y $w 2 [mc Magic]"
    $w.barreGauche.p bind motif(Select) <Button-1> "queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0"
    $w.barreGauche.p bind motif(Del1) <Button-1> "queCreerDetruirePTLPTF $w 0 0 0 0 1 1 1 1"
    $w.barreGauche.p bind motif(Del2) <Button-1> "queCreerDetruirePTLPTF $w 0 0 0 0 1 1 1 1"
    $w.barreGauche.p bind motif(Del1) <Any-Enter> "afficheHelp %x %y $w 1 [mc Delete]" 
    $w.barreGauche.p bind motif(Del2) <Any-Enter> "afficheHelp %x %y $w 1 [mc Delete]" 

    $w.barreGauche.p bind motif(Select) <Any-Enter> "afficheHelp %x %y $w 0 [mc Select]"    
    $w.barreGauche.p bind boutonDessin(0) <Any-Enter> "afficheHelp %x %y $w 0 [mc Select]"    
    $w.barreGauche.p bind boutonDessin(1) <Any-Enter> "afficheHelp %x %y $w 1 [mc Delete]"    
    $w.barreGauche.p bind boutonDessin(2) <Any-Enter> "afficheHelp %x %y $w 2 [mc Magic]"
    $w.barreGauche.p bind boutonDessin(3) <Any-Enter> "afficheHelp %x %y $w 3 [mc Place]"
    $w.barreGauche.p bind boutonDessin(4) <Any-Enter> "afficheHelp %x %y $w 4 [mc Token]"
    $w.barreGauche.p bind boutonDessin(5) <Any-Enter> "afficheHelp %x %y $w 5 [mc Transition]"
    $w.barreGauche.p bind boutonDessin(6) <Any-Enter> "afficheHelp %x %y $w 6 [mc Arc]"
    $w.barreGauche.p bind boutonDessin(7) <Any-Enter> "afficheHelp %x %y $w 7 [mc Nail]"
    $w.barreGauche.p bind boutonDessin(2) <Button-1> "queCreerDetruirePTLPTF $w -2 -1 -1 0 0 0 0 0"
    $w.barreGauche.p bind boutonDessin(3) <Button-1> "queCreerDetruirePTLPTF $w 1 0 0 0 0 0 0 0"
    $w.barreGauche.p bind boutonDessin(4) <Button-1> "queCreerDetruirePTLPTF $w 2 0 0 0 0 0 0 0"
    $w.barreGauche.p bind boutonDessin(5) <Button-1> "queCreerDetruirePTLPTF $w 0 1 0 0 0 0 0 0"
    $w.barreGauche.p bind boutonDessin(6) <Button-1> "queCreerDetruirePTLPTF $w 0 0 1 0 0 0 0 0"
    $w.barreGauche.p bind boutonDessin(7) <Button-1> "queCreerDetruirePTLPTF $w 0 0 0 1 0 0 0 0"
    $w.barreGauche.p bind motif(Eclair) <Button-1> "queCreerDetruirePTLPTF $w -2 -1 -1 0 0 0 0 0"
    $w.barreGauche.p bind motif(Place) <Button-1> "queCreerDetruirePTLPTF $w 1 0 0 0 0 0 0 0"
    $w.barreGauche.p bind motif(Place) <Any-Enter> "afficheHelp %x %y $w 3 [mc Place]"
    $w.barreGauche.p bind motif(Token) <Button-1> "queCreerDetruirePTLPTF $w 2 0 0 0 0 0 0 0"
    $w.barreGauche.p bind motif(Token) <Any-Enter> "afficheHelp %x %y $w 4 [mc Token]"
    $w.barreGauche.p bind motif(Transition) <Button-1> "queCreerDetruirePTLPTF $w 0 1 0 0 0 0 0 0"
    $w.barreGauche.p bind motif(Transition) <Any-Enter> "afficheHelp %x %y $w 5 [mc Transition]"
    $w.barreGauche.p bind motif(Arc) <Button-1> "queCreerDetruirePTLPTF $w 0 0 1 0 0 0 0 0"
    $w.barreGauche.p bind motif(ArcNoeud) <Button-1> "queCreerDetruirePTLPTF $w 0 0 0 1 0 0 0 0"
    $w.barreGauche.p bind motif(Noeud) <Button-1> "queCreerDetruirePTLPTF $w 0 0 0 1 0 0 0 0"
    $w.barreGauche.p bind motif(Arc) <Any-Enter> "afficheHelp %x %y $w 6 [mc Arc]"
    $w.barreGauche.p bind motif(ArcNoeud) <Any-Enter> "afficheHelp %x %y $w 7 [mc Nail]"
    
    canvas $w.barreGauche.seph -width 20 -height 160 
    pack $w.barreGauche.seph -side top

    set newWidth  [expr {21 * $::scaleBD*1.2}]
    set newHeight [expr {$::haut * $::scaleBD *1.2}]

    $w.barreGauche.p configure -width $newWidth -height $newHeight
    $w.barreGauche.p scale all 0 0 [expr $::scaleBD*1.2] [expr $::scaleBD*1.2]


}


 proc afficheHelp {px py w val msg} {
     global zoom
     global dejaHelp

  if {$dejaHelp!=$val} {

      
      set dejaHelp $val
      set val [expr $val*$::scaleBD]
	set x [expr [winfo x .romeo]+[winfo x $w.barreGauche]]
	set y [expr [winfo y $w.barreGauche]+[winfo y $w.barreGauche.p]-40]
    set c $w.frame.c

    $c delete helpText
    $c delete help

    set x [posX $c 1] 
    set y [posY $c $y] 

#set offset [expr int(125/($zoom))-100*int($zoom)]
      set offset [expr ($val*30-30)/$zoom]

 #   set motifHelp [$c create rect [expr $x] [expr $y+$offset-5] \
#				     [expr $x+15+[string length $msg]*5] [expr  $y+$offset+5]  -outline black\
		     -fill white]
    set textHelp [$c create text [expr $x+10/$zoom+[string length $msg]*3/$zoom] [expr $y+$offset] \
				     -text $msg -justify left]
#     $c addtag help withtag $motifHelp
$c addtag helpText withtag $textHelp

 $c scale help 0 0 $zoom $zoom 
 $c scale helpText 0 0 $zoom $zoom 
    update
    after 800 { 
      .romeo.global.frame.c delete helpText
      .romeo.global.frame.c delete help
            update
            set dejaHelp -1
    }
 }
#     if {[winfo exists .help]} {destroy .help} 
 #      set dejaHelp(etat) -1   
 #      set dejaHelp(bouton) -1      

    
}

proc escapeBarreDessin {w} {
    global eclair creerPlace creerTransition

    if {($creerPlace<=-1)&&($creerTransition<=-1)} {
	queCreerDetruirePTLPTF $w -2 -1 -1 0 0 0 0 0
    } else {
	queCreerDetruirePTLPTF $w 0 0 0 0 0 0 0 0
    }
}

proc def4K {u} {
    return [expr {$u * [tk scaling]}]
}

