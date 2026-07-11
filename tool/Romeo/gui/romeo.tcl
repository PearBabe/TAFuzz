# This file is part of the Roméo model-checking software
# 
# Copyright University of Nantes, École Centrale de Nantes, IRCCyN
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


#package require Img
package require xml
package require BWidget
# import les fonctions i18n
namespace import ::msgcat::*


global cheminFichiers
global modif
global nomRdP
global declaration timedCost
global initialization
global tabPlace
global tabTransition
global tabConstraint
global nbConstraints
global tpn tabUnDo
global listeOnglets
global project projet
global semaphore

global tabFlechePT
global tabFlecheTP
global tabNoeud
global tabColor defaultTabColor couleurCourante
global newFPT
global newFTP
global nbProcesseur
global deltaX
global deltaY
global maxX
global maxY
global zoom viewOnglet
global grille
global computOption
global synchronized
#global constraints

global versionRomeo
global dos plateforme 
global editAuto
global francais
global gpnU gpnK tpn2taU tpn2taK

# Initialisation des variables booleennes globales
global fin
global ok
global destroy
global detruirePlace
global detruireTransition
global detruireFleche
global creerLien
global creerPlace
global creerTransition
global creerNoeud
global detruireNoeud
global allowedArc scheduling typePN parameters cost controle
global hideGU
global infini
global parser
global select
global quadrillage
global optionTrace optionSize
global simulatorOn
global simulator
global cheminPref cheminTemp
global dimension
global firstTime
global property
global useReducUnion useReducExplo usePDBM usePDBMsplit
global timedTrace absolute negcost feff
global uneSequence
global boutonIdentifier
global afficheSimu

global semExclusion
global semExclusionDessin
global semExclusionElement

global couleurPN
global avecDeveloppementEncours
global sepColor 
global zoneOuClasseSpace
global stateSpacefileType stateinfigure convergence
global zoomFactor
global nbIterationForcedDirected force distanceMin
global nbTokenColor
global tpn
global eclair

set eclair(slave) 0
set nbIterationForcedDirected 100
set force 10000
set distanceMin 20
set ::constante_ressort 5000
set ::largeur_totale 2600
set ::hauteur_totale 2600
set ::largeur_visible 1000
set ::hauteur_visible 800


set   zoomFactor 1
set usePDBMsplit 0
set zoneOuClasseSpace 0
set stateinfigure 1
set stateSpacefileType "jpg"
set convergence 0

set sepColor "__"

set semExclusionElement 1

set afficheSimu 0
set boutonIdentifier 1
set avecDeveloppementEncours 1

set property ""
set usePDBM 1
set useReducUnion 1
set useReducExplo 1
set timedTrace 0
set negcost 0
set feff 0
set absolute 0
set uneSequence " "

set firstTime(menu) 1
set firstTime(control) 1

global basePath
set basePath [file normalize [file dirname [info script]]]

# path to romeo
global romeoPath
set romeoPath "$basePath/"

# initialisation des variables globales
set dimension(place) 8
set dimension(hauteurTransition) 4
set dimension(largeurTransition) 12
set dimension(jeton) 2
set dimension(noeud) 2
set dimension(flush) 4

set parameters 0
set cost 0
set controle 0
set scheduling 0
# 1 pour ttpn, 2 pour ptpn
set typePN 1
set couleurPN 0

set hideGU(guard) 0
set hideGU(update) 0
set hideGU(Plabel) 0
set hideGU(Pidentifier) 0
set hideGU(Tlabel) 0
set hideGU(Tidentifier) 0
set allowedArc(reset) 1
set allowedArc(read) 1
set allowedArc(logicInhibitor) 1
set allowedArc(timedInhibitor) 0
set computOption(node) -1
set computOption(token) 50000
set computOption(event) -1
set computOption(depth) -1
set computOption(hull) 2
set couleurCourante(Arc) 0
set couleurCourante(Place) 0
set couleurCourante(Transition) 0

 set defaultTabColor(Arc,-1) brown
 set defaultTabColor(Arc,0) black
 set defaultTabColor(Arc,1) gray
 set defaultTabColor(Arc,2) blue
 set defaultTabColor(Arc,3) #beb760
 set defaultTabColor(Arc,4) #be5c7e
 set defaultTabColor(Arc,5) #46be90
 set defaultTabColor(Arc,5) #46be90
 set defaultTabColor(Arc,6) red
 set defaultTabColor(Arc,7) green
 set defaultTabColor(Arc,8) SkyBlue2
 set defaultTabColor(Arc,9) #46be20
 set defaultTabColor(Arc,10) #49be90
 set defaultTabColor(Arc,11) #26be90
 set defaultTabColor(Arc,12) #16be30
 set defaultTabColor(Arc,13) #34be80
 set defaultTabColor(Arc,14) #42be90
 set defaultTabColor(Place,0) SkyBlue2
 set defaultTabColor(Place,1) gray
 set defaultTabColor(Place,2) cyan
 set defaultTabColor(Place,3) green
 set defaultTabColor(Place,4) yellow
 set defaultTabColor(Place,5) brown
 set defaultTabColor(Transition,0) yellow
 set defaultTabColor(Transition,1) gray
 set defaultTabColor(Transition,2) cyan
 set defaultTabColor(Transition,3) green
 set defaultTabColor(Transition,4) SkyBlue2
 set defaultTabColor(Transition,5) brown
 set defaultTabColor(simulator,enabledTrans) brown
 set defaultTabColor(simulator,firableTrans) green
 set defaultTabColor(simulator,noEnabledTrans) lightGray


for {set i 0} {$i <= 5}   {incr i} {
  set tabColor(Place,$i) $defaultTabColor(Place,$i)
  set tabColor(Transition,$i) $defaultTabColor(Transition,$i)
}
for {set i -1} {$i <= 14}   {incr i} {
  set tabColor(Arc,$i) $defaultTabColor(Arc,$i)
}
 set tabColor(simulator,enabledTrans) brown
 set tabColor(simulator,firableTrans) green
 set tabColor(simulator,noEnabledTrans) lightGray

# set tabColor(simulator,enabledTrans) red
# set tabColor(simulator,firableTrans) blue
# set tabColor(simulator,noEnabledTrans) yellow


set select(tpn) 0
set select(etat) 0
set select(x1) 1
set select(x2) 1
set select(y1) 1
set select(y2) 1
set select(vide) 1
set select(red) 0
set select(listePlace) [list]
set select(listeLabelPlace) [list]
set select(listeTransition) [list]
set select(listeLabelTransition) [list]
set select(listeNoeud) [list]
set simulatorOn 0
set simulator(ok) 0
set synchronized [list]

set listeOnglets(tpn) [list]
set listeOnglets(indice) [list]

set tabNoeud(1,arc) 0

set infini 10000000
set francais 0
set dos 1
set editAuto 1
set deltaX 0
set deltaY 0
set creerLien 0
set creerPlace 0
set creerTransition 0
set creerNoeud 0
set detruireNoeud 0
set ok 11
set fin 12
set destroy 13
set detruirePlace 0
set detruireTransition 0
set detruireFleche 0
set modif(0) 0
set modif(freeze) 0
set semaphore(Release) 1

set semExclusion 1
set semExclusionDessin 1

# definition de la taille par defaut de la fenetre de saisie du TPN
# (dedonner dans map)
set maxX 1600
set maxY 1130
set grille 2

set quadrillage 1
set zoom 1
set viewOnglet(zoom,0) 1
set viewOnglet(X,0) 0
set viewOnglet(Y,0) 0

#option du check :
set optionTrace 1
set optionSize 0

font create font1 -family Times -size 12
font create fontPetit -family Times -size 12



font create fontEditor -family [font actual TkDefaultFont -family] -size 12
#font create fontEditor -family Courrier -size 12

set ::menuFontSize [expr [font actual TkDefaultFont -size]+1]

set ::sizeBouton 32
set ::scaleBD 1.1
set ::eparcs 1.8

tk_setPalette background lightgray disabledBackground gray

# specific to MacOSX
if {$tcl_platform(os) == "Darwin"} {
    set tk::mac::useCGDrawing 1
    #    set tk::mac::CGAntialiasLimit 1
}

#**********************************************************************
set versionRomeo "Romeo v3.10.2"

set plateforme $tcl_platform(platform)
set ::osplateforme $tcl_platform(os)
set ::plateforme $tcl_platform(platform)
#if {[string compare $plateforme "windows"]} {
#    set plateforme $tcl_platform(os)
#}
puts "$versionRomeo on $::plateforme platform"

set rienQuePourMoi 0

	    
source "$basePath/scripts/map.tcl"
source "$basePath/scripts/user_pref.tcl"
source "$basePath/scripts/manifich.tcl"
source "$basePath/scripts/manitag.tcl"
source "$basePath/scripts/maniauto.tcl"
source "$basePath/scripts/xmltpn.tcl"
source "$basePath/scripts/place.tcl"
source "$basePath/scripts/masterSlave.tcl"
source "$basePath/scripts/parameters.tcl"
source "$basePath/scripts/controlPanel.tcl"
source "$basePath/scripts/manitpn.tcl"
source "$basePath/scripts/veriftpn.tcl"
source "$basePath/scripts/export.tcl"
source "$basePath/scripts/synchro.tcl"
source "$basePath/scripts/onglet.tcl"
source "$basePath/scripts/unfold.tcl"
source "$basePath/scripts/stateSpace.tcl"
source "$basePath/scripts/cts.tcl"
source "$basePath/scripts/colorationSyntaxique.tcl"
source "$basePath/scripts/dessinRdP.tcl"
source "$basePath/scripts/simulator.tcl"
source "$basePath/scripts/structural.tcl"

source "$basePath/scripts/graphe.tcl"


#source "$basePath/scripts/manage.tcl"

#chemin

set cheminPref [preferences_dir]
set cheminFichiers "./"


if {[file exists [preferences_filename]]} {
    # load pref
    load_preferences
} elseif {![file exists [preferences_dir]]} {
    file mkdir [preferences_dir]
    save_default_preferences
} else {
    save_default_preferences
}
load_preferences
if {![file exists [temp_dir]]} {
    file mkdir [temp_dir]
}


set cheminTemp [temp_dir]
#}

set ::sizeBouton [expr 25*$::scaleBD]

font configure fontEditor -size $fontSizeEditor
font create menufont -family [font actual TkDefaultFont -family] -size $::menuFontSize

#*************************************INIT DEV EN COURS
if {$controle==1} {
    set cost 0
}
#*************************************

# update_locale
proc update_locale {} {
    global francais
    if {$francais == 1} {
	mclocale fr

    } else {
	mclocale en
    }	
}

#Selection de la locale
update_locale 
#chargement des fichiers (dans msgs)
mcload [file join $basePath msgs]


#*******************************************************************
# initialisation***********
set project(nbTPN) 0
set tpn(courant) 0
set tpn(onglet) 0

set tabUnDo($tpn(onglet),courant) 0

set projet($tpn(onglet),nbInclude) 0
set projet($tpn(onglet),include,0,file) ""
set projet($tpn(onglet),nbInput) 0
set projet($tpn(onglet),nbOpen) 0
set projet($tpn(onglet),input,0,file) ""
set projet($tpn(onglet),input,0,status) "closed"

set nbProcesseur($tpn(courant)) 0
set nomRdP($tpn(courant)) "noName.xml"

# Statut des places : ok, detroy, ou fin
set tabPlace($tpn(courant),1,statut) $fin
set tabTransition($tpn(courant),1,statut) $fin

set tabConstraint($tpn(courant),0) ""
set nbConstraints($tpn(courant)) 1

set declaration($tpn(courant)) ""
set initialization($tpn(courant)) "initially \{ \n\n\}"

set timedCost($tpn(courant)) ""

set nbTokenColor($tpn(courant)) 0

set newFTP(transition) 0
set newFPT(place) 0


if {$typePN==-2} { set parameters 0}

#********************************************************************
#init du parser xml

if {[catch {package require expat 1.0}]} {
    if {[catch {package require xml}]} {
	#           error "unable to load a XMLparser"
	set button [tk_messageBox -icon error -message [mc "Unable to load a XMLparser \n\n\ Install    \"expat\" \n          or   \"tcltk 8.4.7 (Activetcl or tclAqua) \""]]
    } else { set parser [::xml::parser] }
} else {
    set parser [expat xmlparser]
}

#package require xml
#set parser [xml::parser myparser]

$parser configure -elementstartcommand elementDebut \
    -characterdatacommand procData -elementendcommand elementFin

# *************************************************************


procedurePlace



set exemple_dot {
    digraph {
        A -> B;
        B -> C;
        C -> A;
        A -> D;
        D -> E;
        E -> F;
        F -> G;
        G -> D;
    }
}

#dessinerGraphe $exemple_dot


proc perso {} {
    global basePath
    source "$basePath/scripts/manitag.tcl"
    source "$basePath/scripts/manitpn.tcl"

}

#********************************************************************
proc irccyn {} {
    global francais
    global versionRomeo
    global basePath

    set logo .image1
    catch {destroy $logo}
    toplevel $logo
    wm title $logo "LS2N"
    wm iconname $logo "Image1"
    # positionWindow $logo

#    frame $logo.image
    # catch {image delete image1a}
#    image create photo image1a -file "$basePath/img/LOGOSLS2N.tiff"
#    label $logo.image.l1 -image image1a -bd 1 -relief sunken

    # catch {image delete image1b}
#    image create photo image1b -file "$basePath/img/LOGOSLS2N.tiff"
#    label $logo.image.l2 -image image1b -bd 1 -relief sunken

#    pack $logo.image.l1  -side left
#    pack $logo.image.l2  -side right
#    pack $logo.image  -side top

    set copyright "Copyright LS2N (c) All rights reserved\n"


    text $logo.text -width 80 -height 30 -bg white -font fontEditor
    pack $logo.text -side top -expand yes
    $logo.text tag configure rouge -foreground darkred
    $logo.text tag configure bleu -foreground blue
    $logo.text tag configure bleuF -foreground darkblue
    $logo.text tag configure surgris -background #a0b7ce
    $logo.text tag configure souligne -underline on

    $logo.text insert end "\n\n" 
    $logo.text insert end "ROMEO :" surgris       
    $logo.text insert end "    $versionRomeo \n" rouge 
    $logo.text insert end "           $copyright\n" 
    $logo.text insert end "URL:" souligne
    $logo.text insert end "    https:\/\/romeo.ls2n.fr\/ \n" bleuF
    $logo.text insert end "Romeo team:" souligne
    $logo.text insert end "\n            Didier LIME , \n            Remi PARROT ,\n            Olivier H. ROUX \n\n" bleuF
    
    $logo.text insert end "LS2N :" surgris
    $logo.text insert end " Laboratoire des Sciences du Numérique de Nantes \n" rouge
    $logo.text insert end "         Equipe Systemes Temps-Reel\n\n" rouge
    $logo.text insert end " UMR CNRS 6004\n\n" bleu
    $logo.text insert end "URL:" souligne
    $logo.text insert end " http:\/\/ls2n.fr/\n\n" bleuF
    $logo.text insert end "Address:" souligne
    $logo.text insert end " LS2N / ECN
 1 rue de la Noe BP92101
 44321 NANTES Cedex 3 \n" bleuF
}
