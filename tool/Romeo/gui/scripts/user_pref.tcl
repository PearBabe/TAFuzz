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

#
# User Management system
#
# Unix (Linux+MacOsX) -> save pref in ~/.romeo
# Windows -> save pref elsewhere, not decided presently

#
# Load user preferences in sent_array
# The user preferences file must exist

# procedure associe au menu Option : MAP, ecrireMap

     
proc load_preferences {} {
    global cheminFichiers 
    global cheminEditeur 
    global cheminExe
    global dos 
    global editAuto 
    global francais 
    global scheduling parameters allowedArc outFormat typePN cost controle couleurPN
    global maxX maxY grille
    global gpnU gpnK mercutioU mercutioK
     
    global tcl_platform
    global env
    global tabColor defaultTabColor
    global hideGU
    global fontSizeEditor
    global boutonIdentifier


    set target $tcl_platform(platform)
    set prefFile ""
    
    # first check the system
    if {[string compare $target "unix"] == 0} {
        # set to ~/.romeo
        set prefFile [file join $env(HOME) ".romeo/preferences"]
    } else {
        set prefFile [file join $env(HOME) "Preferences/.romeo/preferences"] 
        # set to the directory where is installed the application
        # handle windows platform
    }

    #open prefFile
    set file [open $prefFile r]
    # read the file
    set full_text [read $file]
    close $file
    # split lines
	set lines [split $full_text "\n"]
	#match each line
	foreach line $lines {
#puts $lines
        regexp "(.*):(.*)" $line match title value
        if {$title=="outFormat(ta)"} {
            set outFormat(ta) $value
        } elseif {$title=="outFormat(scg)"} {
            set outFormat(scg) $value
        } elseif { $title=="allowedArc(reset)"} {
            set allowedArc(reset) $value
        } elseif { $title=="allowedArc(read)"} {
            set allowedArc(read) $value
        } elseif { $title=="allowedArc(logicInhibitor)"} {
            set allowedArc(logicInhibitor) $value
        } elseif { $title=="allowedArc(timedInhibitor)"} {
            set allowedArc(timedInhibitor) $value
        } elseif { $title=="tabColor(simulator,enabledTrans)"} {
            set tabColor(simulator,enabledTrans) $value
        } elseif { $title=="tabColor(simulator,firableTrans)"} {
            set tabColor(simulator,firableTrans) $value
        } elseif { $title=="tabColor(simulator,noEnabledTrans)"} {
            set tabColor(simulator,noEnabledTrans) $value
        } else {
            set $title $value
        }

	}
}

#
# Save an array to the user preferences file (overwritte)


proc save_preferences {} {
    global cheminFichiers
    global cheminEditeur 
    global cheminExe
    global dos 
    global editAuto 
    global francais 
    global scheduling parameters allowedArc outFormat typePN cost controle couleurPN
    global maxX maxY grille
    global gpnU gpnK mercutioU mercutioK
    global tabColor defaultTabColor
    global tcl_platform
    global env
    global hideGU
    global fontSizeEditor
    global boutonIdentifier


    
    set target $tcl_platform(platform)
    set prefFile ""
    
    # first check the system
    if {[string compare $target "unix"] == 0} {
        # set to ~/.romeo
        set prefFile [file join $env(HOME) ".romeo/preferences"]
    } else {
        set prefFile [file join $env(HOME) "Preferences/.romeo/preferences"] 
         # set to the directory where is installed the application
        # handle windows platform
    }
    
    #open prefFile
    set file [open $prefFile w]
#    puts $file "outFormat(scg):$outFormat(scg)" 
#    puts $file "outFormat(ta):$outFormat(ta)" 
    puts $file "scheduling:$scheduling" 
    puts $file "typePN:$typePN" 
    puts $file "cost:$cost" 
    puts $file "couleurPN:$couleurPN" 
    puts $file "controle:$controle" 
    puts $file "parameters:$parameters" 
    puts $file "allowedArc(reset):$allowedArc(reset)"
    puts $file "allowedArc(read):$allowedArc(read)"
    puts $file "allowedArc(logicInhibitor):$allowedArc(logicInhibitor)"
    puts $file "allowedArc(timedInhibitor):$allowedArc(timedInhibitor)"
    puts $file "dos:$dos"
    puts $file "editAuto:$editAuto"
    puts $file "francais:$francais"
#    puts $file "cheminExe:$cheminExe" 
    puts $file "cheminFichiers:$cheminFichiers" 
#    puts $file "cheminEditeur:$cheminEditeur" 
    puts $file "maxX:$maxX"
    puts $file "maxY:$maxY"
#    puts $file "gpnU:$gpnU"
#    puts $file "gpnK:$gpnK"
    puts $file "grille:$grille"
#    puts $file "mercutioU:$mercutioU"
#    puts $file "mercutioK:$mercutioK"
    for {set i 0} {$i <= 5}   {incr i} {
      puts $file "tabColor(Arc,$i):$tabColor(Arc,$i)" 
      puts $file "tabColor(Place,$i):$tabColor(Place,$i)" 
      puts $file "tabColor(Transition,$i):$tabColor(Transition,$i)" 
      puts $file "defaultTabColor(Arc,$i):$defaultTabColor(Arc,$i)" 
      puts $file "defaultTabColor(Place,$i):$defaultTabColor(Place,$i)" 
      puts $file "defaultTabColor(Transition,$i):$defaultTabColor(Transition,$i)" 
    }
    puts $file "tabColor(simulator,enabledTrans):$tabColor(simulator,enabledTrans)"
    puts $file "tabColor(simulator,firableTrans):$tabColor(simulator,firableTrans)"
    puts $file "tabColor(simulator,noEnabledTrans):$tabColor(simulator,noEnabledTrans)"
    puts $file "defaultTabColor(simulator,enabledTrans):brown"
    puts $file "defaultTabColor(simulator,firableTrans):green"
    puts $file "defaultTabColor(simulator,noEnabledTrans):lightgray"

    puts $file "hideGU(guard):$hideGU(guard)"
    puts $file "hideGU(update):$hideGU(update)"
    puts $file "hideGU(Plabel):$hideGU(Plabel)"
    puts $file "hideGU(Pidentifier):$hideGU(Pidentifier)"
    puts $file "hideGU(Tlabel):$hideGU(Tlabel)"
    puts $file "hideGU(Tidentifier):$hideGU(Tidentifier)"
    puts $file "fontSizeEditor:$fontSizeEditor"
    puts $file "::menuFontSize:$::menuFontSize"
    puts $file "::scaleBD:$::scaleBD"
    puts $file "::eparcs:$::eparcs"
    puts $file "boutonIdentifier:$boutonIdentifier"
    close $file
}

proc preferences_filename {} {
    global tcl_platform
    global env
    set target $tcl_platform(platform)
    set prefFile ""
    # first check the system
    if {[string compare $target "unix"] == 0} {
        # set to ~/.romeo
        set prefFile [file join $env(HOME) ".romeo/preferences"]
    } else {
        set prefFile [file join $env(HOME) "Preferences/.romeo/preferences"] 
         # set to the directory where is installed the application
        # handle windows platform
    }
    return $prefFile
}

proc preferences_dir {} {
    global tcl_platform
    global env
    set target $tcl_platform(platform)
    set prefDir ""
    # first check the system
    if {[string compare $target "unix"] == 0} {
        # set to ~/.romeo
        set prefDir [file join $env(HOME) ".romeo"]
    } else {
        set prefDir [file join $env(HOME) "Preferences/.romeo"] 
        # set to the directory where is installed the application
        # handle windows platform
    }
    return $prefDir
}

proc temp_dir {} {
    global tcl_platform
    global env
    set target $tcl_platform(platform)
    set tempDir ""
    # first check the system
    if {[string compare $target "unix"] == 0} {
        # set to ~/.romeo
        set tempDir [file join $env(HOME) ".romeo/temp"]
    } else {
        set tempDir [file join $env(HOME) "Preferences/.romeo/temp"] 
        # set to the directory where is installed the application
        # handle windows platform
    }
    return $tempDir
}


proc save_default_preferences {} {    
    global tcl_platform
    global env
    global hideGU

    
    set target $tcl_platform(platform)
    set prefFile ""
    
    # first check the system
    if {[string compare $target "unix"] == 0} {
        # set to ~/.romeo
        set prefFile [file join $env(HOME) ".romeo/preferences"]
    } else {
        set prefFile [file join $env(HOME) "Preferences/.romeo/preferences"] 
         # set to the directory where is installed the application
        # handle windows platform
    }
    
    #open prefFile
    set file [open $prefFile w]
    puts $file "outFormat(scg):1" 
    puts $file "outFormat(ta):1" 
    puts $file "scheduling:0" 
    puts $file "typePN:1" 
    puts $file "cost:0" 
    puts $file "controle:0" 
    puts $file "allowedArc(reset):1"
    puts $file "allowedArc(read):1"
    puts $file "allowedArc(logicInhibitor):1"
    puts $file "allowedArc(timedInhibitor):0"
    puts $file "dos:0"
    puts $file "editAuto:0"
    puts $file "francais:0"
    puts $file "cheminExe:." 
    puts $file "cheminFichiers:." 
    puts $file "cheminEditeur:." 
    puts $file "maxX:1900"
    puts $file "maxY:900"
    puts $file "grille:1"
    puts $file "gpnU:1"
    puts $file "gpnK:1"
    puts $file "mercutioU:0"
    puts $file "mercutioK:0"
    puts $file "tabColor(Arc,0):black"
    puts $file "tabColor(Arc,1):gray"
    puts $file "tabColor(Arc,2):blue"
    puts $file "tabColor(Arc,3):#beb760"
    puts $file "tabColor(Arc,4):#be5c7e"
    puts $file "tabColor(Arc,5):#46be90"
    puts $file "tabColor(Transition,0):yellow"
    puts $file "tabColor(Transition,1):gray"
    puts $file "tabColor(Transition,2):cyan"
    puts $file "tabColor(Transition,3):green"
    puts $file "tabColor(Transition,4):SkyBlue2"
    puts $file "tabColor(Transition,5):brown"
    puts $file "tabColor(Place,0):SkyBlue2"
    puts $file "tabColor(Place,1):gray"
    puts $file "tabColor(Place,2):cyan"
    puts $file "tabColor(Place,3):green"
    puts $file "tabColor(Place,4):yellow"
    puts $file "tabColor(Place,5):brown"
    puts $file "defaultTabColor(Arc,0):black"
    puts $file "defaultTabColor(Arc,1):gray"
    puts $file "defaultTabColor(Arc,2):blue"
    puts $file "defaultTabColor(Arc,3):#beb760"
    puts $file "defaultTabColor(Arc,4):#be5c7e"
    puts $file "defaultTabColor(Arc,5):#46be90"
    puts $file "defaultTabColor(Transition,0):yellow"
    puts $file "defaultTabColor(Transition,1):gray"
    puts $file "defaultTabColor(Transition,2):cyan"
    puts $file "defaultTabColor(Transition,3):green"
    puts $file "defaultTabColor(Transition,4):SkyBlue2"
    puts $file "defaultTabColor(Transition,5):brown"
    puts $file "defaultTabColor(Place,0):SkyBlue2"
    puts $file "defaultTabColor(Place,1):gray"
    puts $file "defaultTabColor(Place,2):cyan"
    puts $file "defaultTabColor(Place,3):green"
    puts $file "defaultTabColor(Place,4):yellow"
    puts $file "defaultTabColor(Place,5):brown"
    puts $file "tabColor(simulator,enabledTrans):brown"
    puts $file "tabColor(simulator,firableTrans):green"
    puts $file "tabColor(simulator,noEnabledTrans):lightgray"
    puts $file "defaultTabColor(simulator,enabledTrans):brown"
    puts $file "defaultTabColor(simulator,firableTrans):green"
    puts $file "defaultTabColor(simulator,noEnabledTrans):lightgray"
    puts $file "hideGU(guard):0"
    puts $file "hideGU(update):0"
    puts $file "fontSizeEditor:12"
    puts $file "::menuFontSize:13"
    puts $file "boutonIdentifier:1"
    puts $file "::scaleBD:1.2"
    puts $file "::eparcs:1.5"

    close $file
}


proc load_LastOpenFile {w c} {
     
    global tcl_platform
    global env

    set target $tcl_platform(platform)
    set lastOpenFile ""
    
    # first check the system
    if {[string compare $target "unix"] == 0} {
        # set to ~/.romeo
        set lastOpenFile [file join $env(HOME) ".romeo/lastOpen"]
    } else {
#loaderences"] 
        set lastOpenFile [file join $env(HOME) "Preferences/.romeo/lastOpen"]
        # set to the directory where is installed the application
        # handle windows platform
    }
    
   if {[file exists $lastOpenFile]} {

      #open prefFile
      set file [open $lastOpenFile r]
      # read the file
      gets $file fileName 
      close $file
      if {[file exists $fileName]} {
         ouvrirPointXML $w $c 0 $fileName
      } else { 
         nouveauRdP $w $c
      }
   } else { 
         nouveauRdP $w $c
   }
      
}

proc save_LastOpenFile {fileName} {
     
    global tcl_platform
    global env

    set target $tcl_platform(platform)
    set lastOpenFile ""
    
    # first check the system
    if {[string compare $target "unix"] == 0} {
        # set to ~/.romeo
        set lastOpenFile [file join $env(HOME) ".romeo/lastOpen"]
    } else {
#preferences"] 
        set lastOpenFile [file join $env(HOME) "Preferences/.romeo/lastOpen"]
        # set to the directory where is installed the application
        # handle windows platform
    }
    
      #open prefFile
      set file [open $lastOpenFile w]
      # read the file
      puts $file $fileName 
      close $file
}


#******** MISE a JOUR du chemin OPTION MAP ***************

proc MAP {w c} {
    global cheminExe cheminPref
    global cheminFichiers
    global cheminEditeur
    global dos
    global editAuto
    global francais
    global cheminExe
    global typePN allowedArc outFormat cost controle couleurPN 
    global maxX maxY grille
    global gpnU gpnK mercutioU mercutioK
    global couleurCourante tabColor resultatCouleur tabColorLocal defaultTabColor
    global fontSizeEditor
    global ancienEparcs

#    set ancienSchedule $scheduling
 
    set ancienEparcs $::eparcs
    set top .fenetreHome
    catch {destroy $top}
    toplevel $top
    wm title $top "options"

    $top config 

    frame $top.fcheminFichiers -bd 2 
    entry $top.fcheminFichiers.saisieCheminFichiers -justify left -textvariable cheminFichiers -relief sunken -width 70 -bg white -font fontEditor
    label $top.fcheminFichiers.labelCheminFichiers 
    pack $top.fcheminFichiers.labelCheminFichiers -side left
    pack $top.fcheminFichiers.saisieCheminFichiers -side left
    $top.fcheminFichiers.labelCheminFichiers config -text [mc "Work Directory: "] -font menufont

    button $top.fcheminFichiers.browse -text [mc "Browse"] -font menufont -command  "browseChemin $top" 
    pack $top.fcheminFichiers.browse  -side right -expand 1
    pack $top.fcheminFichiers -side top -fill x

#    frame $top.fcheminExe -bd 2 
#    entry $top.fcheminExe.saisieCheminExe -justify left -textvariable cheminExe -relief sunken -width 50 -bg white
#    label $top.fcheminExe.labelCheminExe 
#    pack $top.fcheminExe.labelCheminExe -side left
#    pack $top.fcheminExe.saisieCheminExe -side right
#    $top.fcheminExe.labelCheminExe config -text [mc "Bin Directory: "]
#    pack $top.fcheminExe -side top -fill x

    # taille de la fenetre

    frame $top.dimension -bd 2 
    entry $top.dimension.saisieX -justify left -textvariable maxX -relief sunken -width 7 -bg white -font fontEditor
    entry $top.dimension.saisieY -justify left -textvariable maxY -relief sunken -width 7 -bg white -font fontEditor
    label $top.dimension.label 
    pack $top.dimension.label -side left
    pack $top.dimension.saisieX -side left
    pack $top.dimension.saisieY -side left
    $top.dimension.label config -text [mc "Window size (x,y): "] -font menufont
    pack $top.dimension -side top -fill x


    frame $top.epaisseurArc -bd 1 
    entry $top.epaisseurArc.saisie -justify left -textvariable ::eparcs -relief sunken -width 3 -bg white -font fontEditor
    label $top.epaisseurArc.label 
    pack $top.epaisseurArc.label -side left
    pack $top.epaisseurArc.saisie -side left
    $top.epaisseurArc.label config -text "Arc width" -font menufont
    pack $top.epaisseurArc -side top -fill x

    
    frame $top.coche -relief ridge -bd 1 
    pack $top.coche -side top -fill x

    frame $top.coche.menufont -relief ridge -bd 1 
    pack $top.coche.menufont -side left 
    
    frame $top.coche.editorfont -relief ridge -bd 1 
    pack $top.coche.editorfont -side left 

    frame $top.coche.menudessin -relief ridge -bd 1 
    pack $top.coche.menudessin -side left

    
    frame $top.coche.grille -relief ridge -bd 1 
    pack $top.coche.grille -side left
#    frame $top.coche.langue -relief ridge -bd 1 
#    pack $top.coche.langue -side left


    label $top.coche.menufont.leLabel -text "Menu font size" -font menufont
    label $top.coche.menufont.sizeLabel  -textvariable ::menuFontSize -font menufont
    
button $top.coche.menufont.plus  -text "+" -font menufont -command menu_font_increase
button $top.coche.menufont.minus -text "−" -font menufont -command menu_font_decrease

pack $top.coche.menufont.leLabel -side top 
pack $top.coche.menufont.sizeLabel -side top 
    
    pack $top.coche.menufont.plus $top.coche.menufont.minus -side left -padx 5
    

    label $top.coche.editorfont.leLabel -text "Editor font size" -font fontEditor
    label $top.coche.editorfont.sizeLabel  -textvariable fontSizeEditor -font fontEditor
    

    pack $top.coche.editorfont.leLabel -side top
    pack $top.coche.editorfont.sizeLabel -side top

    button $top.coche.editorfont.plus  -text "+" -font fontEditor -command editor_font_increase
    button $top.coche.editorfont.minus -text "−" -font fontEditor -command editor_font_decrease

    
    pack $top.coche.editorfont.plus $top.coche.editorfont.minus -side left -padx 5


    label $top.coche.menudessin.leLabel -text "Button design scale"  -font menufont
    label $top.coche.menudessin.sizeLabel  -textvariable ::scaleBD -font menufont

    pack $top.coche.menudessin.leLabel -side top
    pack $top.coche.menudessin.sizeLabel -side top

    button $top.coche.menudessin.plus  -text "+"  -command drawing_scale_increase
    button $top.coche.menudessin.minus -text "−"  -command drawing_scale_decrease

    
    pack $top.coche.menudessin.plus $top.coche.menudessin.minus -side left -padx 5


    

    label $top.coche.grille.titre -text "Magnetic Grid Step: " -font menufont
    pack $top.coche.grille.titre -side top -anchor w


    radiobutton $top.coche.grille.non -text "0" -font menufont -variable grille -value 0 -width 16 -selectcolor red
    pack $top.coche.grille.non -side top

    radiobutton $top.coche.grille.demi -text "1/2" -font menufont -variable grille -value 1 -width 16 -selectcolor red
    pack $top.coche.grille.demi -side top

    radiobutton $top.coche.grille.un -text "1"  -font menufont -variable grille -value 2 -width 16 -selectcolor red
    pack $top.coche.grille.un -side top

#    radiobutton $top.coche.langue.francais -text "Fran�ais"  -variable francais -value 1 -width 16 -selectcolor red
#    pack $top.coche.langue.francais -side top

#    radiobutton $top.coche.langue.anglais -text "English"  -variable francais -value 0 -width 16  -selectcolor red
#    pack $top.coche.langue.anglais -side top

    # option de COULEUR ++++++++++++++++++++++++

 frame $top.coche.palette -bd 2 -relief sunken
    pack $top.coche.palette -side top
	label $top.coche.palette.label -text "Simulator Color setup: " -font menufont
	pack $top.coche.palette.label -side top
    button $top.coche.palette.default  -text "Load default Palette"  -command "loadDefaultPaletteSimulator $top.coche.palette" 
    pack $top.coche.palette.default -side top 

    set tabColorLocal(simulator,enabledTrans)  $tabColor(simulator,enabledTrans)
    set tabColorLocal(simulator,firableTrans) $tabColor(simulator,firableTrans)
    set tabColorLocal(simulator,noEnabledTrans)  $tabColor(simulator,noEnabledTrans)


paletteSimulator $top.coche.palette



    #les fichiers des procedures sont dans maniTPN ++++++++++++++++++++++++
    for {set i 0} {$i <= 5}   {incr i} {
      set tabColorLocal(Place,$i) $tabColor(Place,$i) 
      set tabColorLocal(Transition,$i) $tabColor(Transition,$i) 
      set tabColorLocal(Arc,$i) $tabColor(Arc,$i) 
    }
    frame $top.palette -bd 2 -relief sunken
    pack $top.palette -side top
	label $top.palette.label -text [mc "Color setup: "] -font menufont
	pack $top.palette.label -side top
    frame $top.palette.pta -bd 2
    pack $top.palette.pta -side top
    
    frame $top.palette.pta.colorPlace -bd 2
    pack $top.palette.pta.colorPlace -side left
    paletteCouleur $top.palette.pta.colorPlace Place

    frame $top.palette.pta.colorTransition -bd 2
    pack $top.palette.pta.colorTransition -side left
    paletteCouleur $top.palette.pta.colorTransition Transition
    
    frame $top.palette.pta.colorArc -bd 2
    pack $top.palette.pta.colorArc -side left
    paletteCouleur $top.palette.pta.colorArc Arc
 
    frame $top.palette.buttons 
    pack $top.palette.buttons -side bottom -fill x -pady 2m
    button $top.palette.buttons.default -text [mc "Load default palette"] -font menufont -command  "defaultPalette $top.palette.pta" 
    pack $top.palette.buttons.default -side left
    button $top.palette.buttons.savedefault -text [mc "Save as default palette"] -font menufont -command  "saveAsDefaultPalette" 
    pack $top.palette.buttons.savedefault -side left

 
    
    # provisoirement
    set mercutioK 0


    bind $top <Return> "validerChemin $w $c $top $maxX $maxY"
    frame $top.buttons 
    pack $top.buttons -side bottom -fill x -pady 2m
    button $top.buttons.annuler -text [mc "Cancel"] -font menufont -command  "annulerChemin $top" 
    button $top.buttons.accepter -default active  -font menufont -text "Apply"  \
	-command "validerChemin $w $c $top $maxX $maxY"
    pack $top.buttons.accepter $top.buttons.annuler  -side left -expand 1

    # +++ procedures interne � la procedure map

    proc validerChemin {w c fl ancienX ancienY} {
        global cheminFichiers
        global cheminEditeur
        global cheminExe
        global editAuto
        global dos
        global francais
        global typePN allowedArc outFormat cost controle 
	global maxX maxY zoom grille
        global gpnU gpnK mercutioU mercutioK
        global tabColor tabColorLocal
	global fontSizeEditor

        

    set tabColor(simulator,enabledTrans)  $tabColorLocal(simulator,enabledTrans)
    set tabColor(simulator,firableTrans) $tabColorLocal(simulator,firableTrans)
    set tabColor(simulator,noEnabledTrans)  $tabColorLocal(simulator,noEnabledTrans)

#    set fontSizeEditor [expr int($fontSizeEditor)]

    if {$::eparcs > 10} {
	set ::eparcs 10;
    }    
    if {$::eparcs < 1} {
	set ::eparcs 1;
    }    

    if {$fontSizeEditor <=8} {
	set fontSizeEditor 8;
    }    
    if {$fontSizeEditor >=25} {
	set fontSizeEditor 25;
    }   
    font configure fontEditor -size $fontSizeEditor
 
    for {set i 0} {$i <= 5}   {incr i} {
      set tabColor(Place,$i) $tabColorLocal(Place,$i) 
      set tabColor(Transition,$i) $tabColorLocal(Transition,$i) 
      set tabColor(Arc,$i) $tabColorLocal(Arc,$i) 
    }
	set echap [format %f $maxX]
	set echap [format %f $maxY]
	ajusteTaille
	destroy $fl
	set dos 0
	save_preferences
	if {($maxX != $ancienX)||($maxY!=$ancienY)} {
	    #	     destroy $w
	    #	     procedurePlace
	    destroy $w.frame
	    canvasAsc $w $c
	}
	 redessinerRdP $c

    }

    proc annulerChemin {fl} {
        global cheminFichiers
        global cheminEditeur
 	global dos
        global editAuto
	global francais
        global cheminExe
        global typePN allowedArc outFormat cost controle 
	global maxX maxY grille


	destroy $fl
	load_preferences
#	source scripts/map.tcl
#	chemin
    }

    proc browseChemin {top} {
        global cheminFichiers

         if {[file exists $cheminFichiers]} {
            set cheminFichiersReq [tk_chooseDirectory -initialdir $cheminFichiers]
         } else {
                  set cheminFichiersReq [tk_chooseDirectory]
         }
	    if {[string compare $cheminFichiersReq ""]} {
	      set cheminFichiers $cheminFichiersReq
	    }
   update
    }

    # update selected locale
    update_locale

    # fin de la procedure MAP
}

proc ecrireMap {} {
    global cheminFichiers
    global cheminEditeur
    global cheminExe
    global editAuto
    global dos
    global francais
    global typePN allowedArc outFormat cost controle 
    global maxX maxY grille
    global gpnU gpnK mercutioU mercutioK
    global tabColor defaultTabColor

    set fichier "map.tcl"
    set File [open $fichier w]
    puts $File "proc chemin {} {
     global cheminFichiers
     global cheminEditeur 
     global cheminExe
     global dos 
     global editAuto 
     global francais 
     global allowedArc outFormat typePN cost controle
     global maxX maxY 
     global gpnU gpnK mercutioU mercutioK \n 
     set outFormat(scg) $outFormat(scg) 
     set outFormat(ta) $outFormat(ta) 
     set typePN $typePN
     set cost $cost
     set controle $controle
     set allowedArc(reset) $allowedArc(reset) 
     set allowedArc(read) $allowedArc(read) 
     set allowedArc(logicInhibitor) $allowedArc(logicInhibitor) 
     set allowedArc(timedInhibitor) $allowedArc(timedInhibitor) 
     set dos $dos
     set editAuto $editAuto
     set francais $francais
     set cheminExe \"$cheminExe\" 
     set cheminFichiers \"$cheminFichiers\" 
     set cheminEditeur \"$cheminEditeur\" 
     set maxX $maxX
     set maxY $maxY
     set gpnU $gpnU
     set gpnK $gpnK
     set mercutioU $mercutioU
     set mercutioK $mercutioK
    } "
     for {set i 0} {$i <= 5}   {incr i} {
      puts $File "set tabColor(Arc,$i) $tabColor(Arc,$i)" 
     }

    close $File
}


proc paletteSimulator {f} {
global tabColor tabColorLocal

  frame $f.simu -bd 2
    pack $f.simu -side top
    frame $f.simu.noenabT
    pack $f.simu.noenabT -side top
    label  $f.simu.noenabT.couleur -text "Transition Not Enabled " -width 16 -bg $tabColorLocal(simulator,noEnabledTrans)
    button $f.simu.noenabT.palette -bg yellow -text Palette -command "changeColorSimulator $f noEnabledTrans" 
    pack $f.simu.noenabT.couleur -side left 
    pack $f.simu.noenabT.palette -side left 
    pack $f.simu.noenabT -side top
    frame $f.simu.enabT
    pack $f.simu.enabT -side top
    label  $f.simu.enabT.couleur -text "Enabled Transition" -width 16 -bg $tabColorLocal(simulator,enabledTrans)
    button $f.simu.enabT.palette -bg yellow -text Palette  -command "changeColorSimulator $f enabledTrans" 
    pack $f.simu.enabT.couleur -side left 
    pack $f.simu.enabT.palette -side left 
    frame $f.simu.firabT
    pack $f.simu.firabT -side top
    label  $f.simu.firabT.couleur -text "Firable Transition" -width 16 -bg $tabColorLocal(simulator,firableTrans)
    button $f.simu.firabT.palette -bg yellow -text Palette  -command "changeColorSimulator $f firableTrans" 
    pack $f.simu.firabT.couleur -side left 
    pack $f.simu.firabT.palette -side left 
}

proc changeColorSimulator {f typeTrans} {
global tabColor tabColorLocal resultat

 set resultat [tk_chooseColor -initialcolor gray -title "Choose color"]
 if {[string compare $resultat ""]} {
    set tabColorLocal(simulator,$typeTrans) $resultat
   destroy $f.simu
   paletteSimulator $f
  } 
}

proc loadDefaultPaletteSimulator {f} {
global tabColorLocal defaultTabColor

    set tabColorLocal(simulator,enabledTrans)  $defaultTabColor(simulator,enabledTrans)
    set tabColorLocal(simulator,firableTrans) $defaultTabColor(simulator,firableTrans)
    set tabColorLocal(simulator,noEnabledTrans)  $defaultTabColor(simulator,noEnabledTrans)

   destroy $f.simu
   paletteSimulator $f

}

proc menu_font_increase {} {
    set size [font actual menufont -size]
    if {$size < 40} {
	set ::menuFontSize [expr {$size + 2}]
        font configure menufont -size $::menuFontSize
    }
}

proc menu_font_decrease {} {
    set size [font actual menufont -size]
    if {$size > 6} {
	set ::menuFontSize [expr {$size - 2}]
        font configure menufont -size $::menuFontSize
    }
}

proc editor_font_increase {} {
    global  fontSizeEditor

    set size [font actual fontEditor -size]
    if {$size < 25} {
	set fontSizeEditor [expr {$size + 1}]
        font configure fontEditor -size $fontSizeEditor
    }
}

proc editor_font_decrease {} {
    global  fontSizeEditor
    
    set size [font actual fontEditor -size]
    if {$size > 6} {
	set fontSizeEditor [expr {$size - 1}]
        font configure fontEditor -size $fontSizeEditor
    }
}


proc drawing_scale_increase {} {

    if {$::scaleBD < 4} {
	set ancienscaleBD $::scaleBD
	set ::scaleBD [format "%.2f" [expr {$::scaleBD + 0.1}]]
	
	set reduc  [expr {$::scaleBD/$ancienscaleBD}]
	set newWidth  [expr {21 * $::scaleBD*1.2}]
	set newHeight [expr {$::haut * $::scaleBD*1.2}]

	.romeo.global.barreGauche.p configure -width $newWidth -height $newHeight
	.romeo.global.barreGauche.p scale all 0 0 $reduc $reduc
	changerTailleBoutons .romeo.global $reduc
    }
}

proc drawing_scale_decrease {} {
    if {$::scaleBD > 0.4} {
	set ancienscaleBD $::scaleBD
	set ::scaleBD [format "%.2f" [expr {$::scaleBD - 0.1}]]
	
	set reduc  [expr {$::scaleBD/$ancienscaleBD}]
	set newWidth  [expr {21 * $::scaleBD*1.2}]
	set newHeight [expr {$::haut * $::scaleBD *1.2}]

	.romeo.global.barreGauche.p configure -width $newWidth -height $newHeight
	.romeo.global.barreGauche.p scale all 0 0 $reduc $reduc

	changerTailleBoutons .romeo.global $reduc
    }
}

proc changerTailleBoutons {w reduc} {
    set ::sizeBouton  [expr $::sizeBouton*$reduc]
  
    creerBoutonsFichiers $w $w.frame.c $::sizeBouton
    creerBoutonZoom $w $w.frame.c $::sizeBouton
    creerBoutonCopyCut $w $w.frame.c $::sizeBouton

}


