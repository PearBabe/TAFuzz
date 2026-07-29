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

# Verification de propriétés du TPN
# Verification syntaxique des propriété
#verification syntaxique des contraintes
#*********
#*
#procedure checkProperty
#*
#*********
proc afficheDialogue {fp texte} {

    $fp.dialogue.retour.syntax insert end  "$texte"
    $fp.dialogue.retour.syntax yview moveto 1
}


proc emptyFile {thefile} {
    
    set file [open $thefile]
    set ligne [gets $file]
    if {[eof $file] && ($ligne == "")} {
	close $file
	return 1
    } else {
	close $file
	return 0
    }
}


proc checkCTS {property} {
    global nomRdP nomCheck modif useReducUnion useReducExplo usePDBM usePDBMsplit
    global timedTrace negcost feff
    global tpn tabUnDo cost controle
    global cheminTemp computOption
    global romeoPath
    global parameters typePN computOption
    global plateforme
    global theLastTrace
  
    set tpn(courant) [calculTPNCourant 0]


#    if {[file exists $cheminTemp/mercutio.log]} {
#	set glop [catch  {file delete -force $cheminTemp/mercutio.log }]	
#    }
    
    set executable $romeoPath
    append executable "bin/romeo-cli"
    if {[string compare $plateforme "windows"]==0} {
	append executable ".exe"
    }
    set reponse "$cheminTemp/mercutio.ans"
    set syntaxerror "$cheminTemp/mercutio.log"
    set ctsfile "$cheminTemp/ctsfile.cts"

    affiche "\n" 

    set optReduc ""
    if {$timedTrace==-1} {    
	set optReduc ", no_trace"
    } elseif {$timedTrace==2} {
	    set optReduc ", timed_trace, absolute"
    } elseif {$timedTrace==1} {
	    set optReduc ", timed_trace"
    }

    if {$controle==2} {
	set optReduc "$optReduc, zones"
    }
	
    set optionCost ""
    if {$cost>0} {
        if {$negcost==1} {set optionCost ",neg_costs"}
	if {$cost==1} { set optionCost "cost_mode=poly$optionCost"}
	if {$cost==2} { set optionCost "cost_mode=split$optionCost"}
    }


    
    if  {$optionCost != ""} {
	set optReduc ", $optionCost$optReduc"
	#	set optReduc "$optReduc, $optionCost$optReduc"
    }

    if {$useReducUnion == 0 } {
	set optReduc "$optReduc, nored"
    }

    if {$feff>0} {set optReduc "$optReduc, feff"}

    if {($usePDBMsplit == 1)&&($parameters>0)} {
       set optReduc "$optReduc, pdbm=split"
       set usePDBM 0
    } elseif {($usePDBM == 1)&&($parameters>0)} {
	set optReduc "$optReduc, pdbm"
    }

    
    if {$useReducExplo == 1 } {
	set optReduc "$optReduc, restrict"
    }

    if {$parameters == 3 } {
	set property "check\[ihc$optReduc\] $property"
	
    } elseif {$parameters == 2 } {
	set property "check\[ip$optReduc\] $property"
	
    } else {
	if  {$optReduc != ""} {
	    set optReduc [supNextExpression $optReduc ","]
	    set property "check \[$optReduc\] $property"
	} else {
	    set property "check $property"
	}
    }
    set CTSprop [calculPropCTS $property]

# on garde pour le moment mais a jeter a priori
    if  {$cost>999} {
# COST COST COST
	set optionCost ""
        if {$negcost==1} {set optionCost ",neg_costs"}
	if {$cost==1} { set CTSprop "check\[cost_mode=poly$optionCost$optReduc\] [calculPropCTS $property]"}
	if {$cost==2} { set CTSprop "check\[cost_mode=split$optionCost$optReduc\] [calculPropCTS $property]"}
#	if {$cost==3} { set CTSprop "check\[cost_mode=optim$optionCost$optReduc\] [calculPropCTS $property]"}
#	if {$cost==4} { set CTSprop "check\[cost_mode=global$optionCost$optReduc\] [calculPropCTS $property]"}
    }
    affiche "-Invoking romeo-cli with formula: "
    afficheBleu  "$property\n"
    afficheMarron  "    \[info\] CTS file: $ctsfile"

#    set nomDeBase [sansXml $nomRdP($tpn(onglet))]
    export2CTS $tpn(courant) $ctsfile "$CTSprop" 0

    # effacer ce qu'il y a dans le fichier de log
      if {[file exists $syntaxerror]} {
	set File [open $syntaxerror w+]
	close $File
    }

    if { [catch {exec $executable -v -m $ctsfile > $reponse 2>> $syntaxerror} erreur] } {

#	puts $erreur
	if {(![file exists $syntaxerror])||[emptyFile $syntaxerror]} {
	  if { ![catch {open $syntaxerror w} fid] } {
	    set File [open $syntaxerror w]
	    puts $File "$erreur"
	    close $File
	  }
      }
  }

 

    update idletasks
}


proc afficheCheck {f optionTrace optionSize} {
    global cheminTemp plateforme
    global tpn tabUnDo
    global theLastTrace


    if {[emptyFile $cheminTemp/mercutio.log]} {
	set fichier "$cheminTemp/mercutio.ans"
    } else {
	set fichier "$cheminTemp/mercutio.log"
    }
    set ctsfile "$cheminTemp/ctsfile.cts"
    set file "glop"
    
    if { [catch {open $fichier r} file] } { 
	  affiche [format [mc "Unable to open %s"] $fichier] 
    } else {
	
#    set message [read $file]
#    $f insert end "$message \n" bleu
    #  if {$optionTrace + $optionSize>0}

    while {![eof $file]} {
      gets $file line
      if {[string compare  [nextExpression $line " "] "Trace:"]==0} {
	  set line [supNextExpression $line " "]
	  $f insert end "Trace: " rouge
          $f insert end "$line" bleu
	  set theLastTrace $line
      } elseif {[string compare  [nextExpression $line " "] "\[info\]"]==0} {
# Afficher le temps d'execution
# et  Max memory used (Unix et macos)
	  set quelleInfo  [supNextExpression $line "\[info\] "]

	  if   {[string compare  [nextExpression $quelleInfo ":"] "Time"]==0} { 
	      afficheMarron "\n    $line"
	  }

	  if   {[string compare  [nextExpression $quelleInfo ":"] "Max memory used"]==0} { 
	      afficheMarron " \n    $line"
	  }

    } elseif {[string compare  [nextExpression $line " "] "\[error\]"]==0} {
# $f insert end "Error in program $line\n" rouge
	  set lineNumber [nextExpression [supNextExpression $line "Line "] ":"]
#set lineNumber 0
	  if {$lineNumber != ""} {
	      set messageErreur [export2CTSgetError $tpn(courant) "" "" $lineNumber 0]
	      set localLineNumber [nextExpression [supNextExpression $messageErreur "(line "] "):"]
	      $f insert end "[nextExpression $messageErreur "@@details**"]" rouge
	      $f insert end "Line $lineNumber in CTS file: $ctsfile \n" bleu
	      $f insert end "[supNextExpression $line ":"] \n" bleu
	      $f insert end "[arroundError $localLineNumber [supNextExpression $messageErreur "@@details**"]] \n" vert
	  } else {
	      $f insert end "$line \n" rouge
	      $f insert end "in CTS file: $ctsfile \n" bleu
	  }
#	  raise .fenetreCheck
    } elseif {[string compare  [nextExpression $line " "] "\[warning\]"]==0} {
	$f insert end "$line \n" vert
	$f insert end "in CTS file: $ctsfile \n" bleu
    } else {
	$f insert end "$line \n" bleu
    }

  }
    close $file


  }
}


proc loadProperty {fp} {
    global property
    global nomRdP 
    global tpn tabUnDo
    global cheminFichiers
    global fileProperty
    global theLastTrace


    afficheDialogue $fp [mc "\n-------\nLoad property ... : \n"]
    set types {
	{"tctl file"     {.tctl}      TEXT}
    }
    set file [tk_getOpenFile -initialdir $cheminFichiers -filetypes $types ]
    if {[string compare $file ""]} {
	set fichier $file
	
	set file [open $fichier r]
	gets $file property
	close $file 
	set fileProperty $fichier
	afficheDialogue $fp  "$property\n"
	$fp.dialogue.fileProperty.nom config -text "$fileProperty"
    }
}
#--------------------------------- Inutile maintenant
proc savePropertyFile {fp} {
    global property
    global nomRdP 
    global tpn tabUnDo
    global optionTrace optionSize optionTraceSize
    global cheminFichiers
    global fileProperty
    global theLastTrace


    if [string compare $fileProperty ""] {
	saveProperty $fp $fileProperty
    } else {
	afficheDialogue $fp [mc "\n-------\nUnable to save -> No file selected\n"]
    }
    $fp.dialogue.retour.syntax yview moveto 1
}
#--------------------------------- fin Inutile maintenant

proc saveProperty {fp nomFichierProperty} {
    global property
    global fileProperty
    global theLastTrace


    if [string compare $nomFichierProperty ""] {
	set File [open $nomFichierProperty w]
	puts $File  "$property"
	close $File
#	afficheDialogue $fp  [format [mc "\n-------\nSave property %s in %s \n"] $property $nomFichierProperty]
	return 1
    } else {
#	afficheDialogue $fp [mc "\n-------\nUnable to save -> No file selected\n"]
	return 0
    }
}


proc savePropertyAs {fp} {
    global property
    global nomRdP 
    global tpn tabUnDo
    global optionTrace optionSize optionTraceSize
    global cheminFichiers
    global fileProperty
    global theLastTrace


    set retour 0
    $fp.dialogue.retour.syntax insert end  [format [mc "\n-------\nSave property %s as ... \n"] $property]
    set types {
	{"tctl file"     {.tctl}      TEXT}
    }
    if [string compare $nomRdP($tpn(onglet)) "noName.xml"] {
        set last [string first ".xml" $nomRdP($tpn(onglet))]
	if {$last>=0} {set nomProperty "[string range $nomRdP($tpn(onglet)) 0 [expr $last -1]]-prop.tctl" }
	set fichier [tk_getSaveFile -filetypes $types  -title [mc "Save property as..."]\
			 -initialdir [repertoire $nomProperty] -initialfile [nomSeul $nomProperty]]
    } else {
        set fichier [tk_getSaveFile -filetypes $types -title [mc "Save property as..."] -initialdir $cheminFichiers -defaultextension .tctl]
    }
    if [string compare $fichier ""] {
	set File [open $fichier w]
	puts $File  "$property"
	close $File
	$fp.dialogue.retour.syntax insert end  "$fichier"
	set fileProperty $fichier
	$fp.dialogue.fileProperty.nom config -text "$fileProperty"
	set retour "1"
    } else {
	$fp.dialogue.retour.syntax insert end  [mc "Cancelled"]
    }
    $fp.dialogue.retour.syntax yview moveto 1
    return $retour
}

proc peutOnChecker {fp} {
    global scheduling typePN
    global nomRdP modif 
    global tpn tabUnDo
    global fileProperty nomCheck
    global property nomCheck
    global cheminTemp
    global theLastTrace


    set retour 0
    set nomCheck "nofile"
    set retour [saveProperty $fp "$cheminTemp/mercutio.que"]

    if {$retour==1} {
#	if {($modif($tpn(courant)) ==1)||(![string compare "$nomRdP($tpn(onglet))" "noName.xml"])} {
#	    set reponse [tk_messageBox -message [mc "Save net?"] -type yesno -icon question]
#	    switch -exact $reponse {
#		yes {
#		    aiguillageEnregistrer .romeo.global
#		    set nomCheck $nomRdP
#		}
#		no {
#		    $fp.dialogue.retour.syntax insert end "\n"
#		    $fp.dialogue.retour.syntax insert end [mc "-Petri net not saved. Checker will run with temporary file TPNCheck.xml"]
#		    set nomCheck "$cheminTemp/TPNcheck.xml"
#		    enregistrerTpnXml "$nomCheck" 0
#	    update idletasks

#		}
#	    }
#	} else {set nomCheck $nomRdP($tpn(onglet)) }
	set nomCheck $nomRdP($tpn(onglet))
    }
    return $retour
}


proc checkDejaOuvert {} {
    global property

 if {[winfo exists .fenetreCheck]} {
    destroy .fenetreCheck
    checkProperty
 }

}


#------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------

proc checkPropertyglop {} {
    global nomRdP
    global francais
    global infini
    global property
    global optionTrace optionTrace optionTraceSize useCTS useReducUnion useReducExplo usePDBM
    global timedTrace  negcost feff
    global fileProperty
    global scheduling parameters typePN
    global nbTrace


  if {$typePN==-2} {
	affiche "\n > Model Checker not available in Scheduling mode"
  } else {

    set useCTS 1
    set optionTraceSize 0
    affiche "\n"
    affiche [mc "-Opening \"on-the-fly checking\" window"]
    set fileProperty ""
    #  set property "M(1) < 2 and M(2) > 3 or M(3) <1"
    set fp .fenetreCheck
    catch {destroy $fp }
    toplevel $fp

    if {[winfo rootx .romeo] > ([winfo screenwidth .romeo]/3)} { set x 10 } else {set x [expr int([winfo screenwidth .romeo]/2)-50]}
    if {[winfo rooty .romeo] > ([winfo screenheight .romeo]/3)} { set y 20 } else {set y [expr int([winfo screenheight .romeo]/2)-10]}
    set hauteurecran [expr  [winfo screenheight .romeo]/10]


 wm geometry $fp 40x25+$x+$y

   

    wm title $fp [mc "On-the-fly TCTL model-checking"]

#    frame $fp.dialogue
#    pack $fp.dialogue -side left -fill both -expand yes
    set f $fp

    # saisie de la propriété
    frame $f.property -bd 2
    entry $f.property.saisieNom -justify left -textvariable property -relief sunken -width 30 -bg white -font fontEditor
    label $f.property.label 
    pack $f.property.saisieNom -side right -fill both -expand yes
    pack $f.property.label -side left
    $f.property.label config -text [mc "Property:"] -font menufont
    pack $f.property -side top -fill both

    frame $f.fileProperty -bd 2 -relief sunken -bg white -width 30
    pack $f.fileProperty -side top -fill both
    label $f.fileProperty.lab
    pack $f.fileProperty.lab -side left
    $f.fileProperty.lab config -text [mc "File:"] -font menufont
    label $f.fileProperty.nom -bg white
    pack $f.fileProperty.nom -side left -fill both
    $f.fileProperty.nom config -text "" -font menufont

    frame $f.saveOpen -bd 2
    pack $f.saveOpen -side top -fill both
    button $f.saveOpen.saveas -text [mc "Save Property as..."] -font menufont \
	-command "savePropertyAs $fp"
    button $f.saveOpen.save -text [mc "Save Property"] -font menufont \
	-command "savePropertyFile $fp"
    button $f.saveOpen.open -text [mc "Load Property"] -font menufont \
	-command "loadProperty $fp"
    pack $f.saveOpen.save $f.saveOpen.saveas $f.saveOpen.open  -side left -expand 1 -fill x

    # message vers l'utilisateur
    frame $fp.retour
    set f1 $fp.retour
    pack $f1 -side top -fill both -expand yes

    text $f1.syntax -yscrollcommand "$f1.vscroll set" -width 50 -height 10 -bg white -wrap word -font fontEditor
    scrollbar $f1.vscroll -command "$f1.syntax yview"
    pack $f1.syntax -side left -fill both -expand yes
    pack $f1.vscroll -side right -fill y

	text $f1.text -yscrollcommand "$f1.vscroll set" -width 50 -height 20 -bg white -wrap word -font fontEditor
	scrollbar $f1.vscroll -command "$f1.text yview"
	pack $f1.text -side left -fill both -expand yes
	pack $f1.vscroll -side right -fill y
	frame $fp.indice -width 10 -height 10
	pack $fp.indice -side right -fill y
    text $fp.indice.text -yscrollcommand "$fp.indice.vscroll set" -setgrid true \
	-width 10 -height 8 -font fontEditor
    scrollbar $fp.indice.vscroll -command "$fp.indice.text yview"
}


}
#------------------------------------------------------------------------------------

#++++++ procedures internes à check property



proc afficheIndicePlace {fi} {
    global tabPlace 
    global tpn tabUnDo
    global fin
    global ok
    global infini
    global theLastTrace


    text $fi.text -yscrollcommand "$fi.vscroll set" -setgrid true \
	-width 20 -height 8 -font fontEditor
    scrollbar $fi.vscroll -command "$fi.text yview"
    # -xscrollcommand "$fi.hscroll set"
    # scrollbar $fi.hscroll -orient horiz -command "$fi.text xview"


    pack $fi.vscroll -side right -fill y
    pack $fi.text -expand yes -fill both
    # pack $fi.hscroll -side bottom -fill x

    $fi.text tag configure rouge -foreground red
    $fi.text tag configure surgris -background #a0b7ce
    $fi.text tag configure souligne -underline on


    $fi.text insert end "  PLACE             \n" souligne
    $fi.text insert end "Index " surgris
    $fi.text insert end "  \"label\" \n" rouge


    # place par place
    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
	if {$tabPlace($tpn(courant),$i,statut)==$ok} {
	    $fi.text insert end "$i " surgris
	    $fi.text insert end "  \"$tabPlace($tpn(courant),$i,label,nom)\"\n" rouge
	}
    }
}

#--------------------------------------------------------------------------------------------
proc checkProperty {} {
    global nomRdP
    global francais
    global infini
    global property
    global optionTrace optionTraceSize useCTS useReducUnion useReducExplo usePDBM
    global timedTrace negcost feff
    global fileProperty
    global scheduling parameters typePN cost controle 
    global nbTrace
    global theLastTrace
    global nbTokenColor
    global tpn 


    set theLastTrace ""


  if {($typePN==-2)&&($controle==0)} {    # Si controle alors le scheduling n'est pas pris en compte donc on peut le laisser
	affiche "\n > Model Checker not available in Scheduling mode"
  } else {

    set useCTS 1
    set optionTraceSize 0
    affiche "\n"
    affiche [mc "-Opening \"on-the-fly checking\" window"]
    set fileProperty ""
    #  set property "M(1) < 2 and M(2) > 3 or M(3) <1"
    set fp .fenetreCheck
    catch {destroy $fp }
    toplevel $fp

    if {[winfo rootx .romeo] > ([winfo screenwidth .romeo]/3)} { set x 10 } else {set x [expr int([winfo screenwidth .romeo]/2)-50]}
    if {[winfo rooty .romeo] > ([winfo screenheight .romeo]/3)} { set y 20 } else {set y [expr int([winfo screenheight .romeo]/2)-10]}
    set hauteurecran [expr  [winfo screenheight .romeo]/10]
 wm geometry $fp 60x25+$x+$y

   

    wm title $fp [mc "On-the-fly TCTL model-checking"]

    frame $fp.dialogue
    pack $fp.dialogue -side left -fill both -expand yes
    set f $fp.dialogue

    # saisie de la propriété
    frame $f.property -bd 2
    entry $f.property.saisieNom -justify left -textvariable property -relief sunken -width 60 -bg white -font fontEditor
    label $f.property.label
    pack $f.property.saisieNom -side right -fill both -expand yes
    pack $f.property.label -side left
    $f.property.label config -text [mc "Property:"] -font menufont 
    pack $f.property -side top -fill both

    frame $f.fileProperty -bd 2 -relief sunken -bg white
    pack $f.fileProperty -side top -fill both
    label $f.fileProperty.lab
    pack $f.fileProperty.lab -side left
    $f.fileProperty.lab config -text [mc "File:"] -font menufont 
    label $f.fileProperty.nom -bg white
    pack $f.fileProperty.nom -side left -fill both
    $f.fileProperty.nom config -text ""

    frame $f.saveOpen -bd 2
    pack $f.saveOpen -side top -fill both
    button $f.saveOpen.saveas -text [mc "Save Property as..."] -font menufont -command "savePropertyAs $fp"
    button $f.saveOpen.save -text [mc "Save Property"] -font menufont \
	-command "savePropertyFile $fp"
    button $f.saveOpen.open -text [mc "Load Property"] -font menufont \
	-command "loadProperty $fp"
    pack $f.saveOpen.save $f.saveOpen.saveas $f.saveOpen.open  -side left -expand 1

    # message vers l'utilisateur
    frame $fp.dialogue.retour
    set f1 $fp.dialogue.retour
    pack $f1 -side top -fill both -expand yes

    text $f1.syntax -yscrollcommand "$f1.vscroll set" -width 60 -height 10 -bg white -wrap word -font fontEditor
    scrollbar $f1.vscroll -command "$f1.syntax yview"
    pack $f1.syntax -side left -fill both -expand yes
    pack $f1.vscroll -side right -fill y
    

    afficheGrammaire $f1

    # affichage des indices des places
   # frame $fp.indice -width 20 -height 10
    ##pack $fp.indice -side right -fill y
    #afficheIndicePlace $fp.indice
   # affichage des indices des places
    frame $fp.indice -width 20 -height 10
    pack $fp.indice -side right -fill y
#    afficheIndicePlace $fp.indice

    text $fp.indice.text -yscrollcommand "$fp.indice.vscroll set" -setgrid true \
	-width 20 -height 8 -font fontEditor
    scrollbar $fp.indice.vscroll -command "$fp.indice.text yview"


    event add <<Echap>> <Escape>
    event add <<load>> <F1>

    bind $fp <Return> "validerCheck $fp"
    bind $fp <<Echap>> "quitterCheck $fp"

    #  bind $fp <<load>>  "source veriftpn.tcl"

    set nbTrace 1

    if {$controle!=1} {

	frame $f.option -relief ridge -bd 1
	pack $f.option -side top -anchor w
	#label $f.option.titre -text [mc "Options:"]
	#pack $f.option.titre -side top -anchor w

	frame $f.option.gauche
	pack $f.option.gauche -side left -anchor w


	frame $f.option.gauche.trace
	pack $f.option.gauche.trace -side top -anchor w -expand yes

	# au lieu de  if {$parameters} je mets ca car l'option tracesize n'est pas disponible pour le moàment
	if {$parameters==243} {
	    frame $f.option.gauche.traceSize
	    pack $f.option.gauche.traceSize -side top -pady 2 -anchor w
	    entry  $f.option.gauche.traceSize.saisie -justify left -textvariable optionTraceSize -relief sunken -width 10 -bg white -font fontEditor
	    pack  $f.option.gauche.traceSize.saisie -side left
	    label $f.option.gauche.traceSize.label -text [mc ": maximum trace size (none if 0)"]       	
	    pack $f.option.gauche.traceSize.label -side left
	}
	#        checkbutton $f.option.gauche.trace.yesno -text "[mc "Give a trace?"]" -variable optionTrace -selectcolor red
        #entry $f.option.gauche.trace.nb -justify left -textvariable nbTrace -relief sunken -width 5 -bg white
	#        pack $f.option.gauche.trace.yesno -side left -anchor w -expand yes
        #pack $f.option.gauche.trace.nb -side right -anchor w -expand yes

	#    frame $f.option.gauche.cts
	#    pack $f.option.gauche.cts -side top -anchor w -expand yes
	#    checkbutton $f.option.gauche.cts.yesno -text "Use new engine ?" -variable useCTS -selectcolor red
	#    pack $f.option.gauche.cts.yesno -side left -anchor w -expand yes

	frame $f.option.gauche.timedtrace -relief solid -bd 1 
	pack $f.option.gauche.timedtrace -side left -anchor w -expand yes
	radiobutton $f.option.gauche.timedtrace.notrace -text "no Trace ?  " -font menufont -variable timedTrace -selectcolor red 
# -command "changeTimedTrace $f"
	pack $f.option.gauche.timedtrace.notrace -side top -anchor w -expand yes
	radiobutton $f.option.gauche.timedtrace.untimedtrace -text "untimed Trace ?  " -font menufont -variable timedTrace  -value 0 -selectcolor red  
#-command "changeTimedTrace $f"
	pack $f.option.gauche.timedtrace.untimedtrace -side top -anchor w -expand yes
	radiobutton $f.option.gauche.timedtrace.trace -text "Timed Trace ?  " -font menufont -variable timedTrace  -value 1 -selectcolor red  
#-command "changeTimedTrace $f"
	pack $f.option.gauche.timedtrace.trace -side top -anchor w -expand yes
	radiobutton $f.option.gauche.timedtrace.absolute -text "Absolute time trace ?  " -font menufont -variable timedTrace  -value 2 -selectcolor red
	pack $f.option.gauche.timedtrace.absolute -side top -anchor w -expand yes
#	if {$timedTrace} {
#	    $f.option.gauche.timedtrace.absolute configure -state active
#	} else {	    
#	    $f.option.gauche.timedtrace.absolute configure -state disabled
#	}
	if {$parameters > 0 } {
	    frame $f.option.gauche.reduc  -relief solid -bd 1
	    pack $f.option.gauche.reduc -side right -anchor w -expand yes
	    checkbutton $f.option.gauche.reduc.reducUnion -text "Try to minimize unions of polyhedra ?" -font menufont -variable useReducUnion -selectcolor red
	    pack $f.option.gauche.reduc.reducUnion -side top -anchor w -expand yes
	    checkbutton $f.option.gauche.reduc.reducExplo -text "Try to restrict exploration to parameter valuations not found already ?" -font menufont -variable useReducExplo -selectcolor red
	    pack $f.option.gauche.reduc.reducExplo -side top -anchor w -expand yes
	    checkbutton $f.option.gauche.reduc.pdbm -text "Use parametric DBMs ? (for closed intervals only)" -font menufont -variable usePDBM  -selectcolor red
	    pack $f.option.gauche.reduc.pdbm -side top -anchor w -expand yes
	    checkbutton $f.option.gauche.reduc.pdbmsplit -text "Use parametric DBMs with spliting ? (for closed intervals only)" -font menufont -variable usePDBMsplit -selectcolor red
	    pack $f.option.gauche.reduc.pdbmsplit -side top -anchor w -expand yes
	}

	if {$cost > 0 } {
	    frame $f.option.gauche.cost  -relief solid -bd 1
	    pack $f.option.gauche.cost -side right -anchor w -expand yes
	    checkbutton $f.option.gauche.cost.negative -text "Negative cost ?" -font menufont -variable negcost -selectcolor red
	    pack $f.option.gauche.cost.negative -side top -anchor w -expand yes
	}
	if {$nbTokenColor($tpn(courant))>0} {
	    frame $f.option.gauche.feff  -relief solid -bd 1
	    pack $f.option.gauche.feff -side right -anchor w -expand yes
	    checkbutton $f.option.gauche.feff.ouinon -text "feff ?" -font menufont -variable feff -selectcolor red
	    pack $f.option.gauche.feff.ouinon -side top -anchor w -expand yes
	}
    }

    #checkbutton $f.option.gauche.size -text [mc "Give graph size (states - zones)"] -variable optionSize -selectcolor red
    #pack $f.option.gauche.size -side top -anchor w -expand yes

    frame $f.buttons -bd 2
    button $f.buttons.annuler -text [mc "Close"] -font menufont -command  "quitterCheck $fp"
    button $f.buttons.accepter -default active -text [mc "Check property"] -font menufont \
	-command "validerCheck $fp"
    button $f.buttons.simulate -text "Simulate the trace" -font menufont -command  "simulateTheTrace .romeo.global .romeo.global.frame.c"
    pack $f.buttons -side bottom -fill both
    pack $f.buttons.accepter  $f.buttons.simulate $f.buttons.annuler  -side left -expand 1


    #++++++ procedures internes à check property
#    proc changeTimedTrace {f} {
#    global timedTrace absolute negcost

#	if {$timedTrace} {
#	    $f.option.gauche.timedtrace.absolute configure -state active
#	} else {	    
#	    $f.option.gauche.timedtrace.absolute configure -state disabled
#	}
#    }

    proc quitterCheck {fp} {
	destroy $fp
	affiche "\n"
	affiche [mc "-\"On-the-fly checking\" window closed"]
    }
    proc validerCheck {fp} {
	global property nomCheck
	global nomRdP modif 
	global tpn tabUnDo
	global optionTrace optionSize nbTrace optionTraceSize useCTS useReducUnion useReducExplo usePDBM usePDBMsplit
	global timedTrace negcost feff
	global fileProperty
	global cheminTemp
	global scheduling typePN cost
	global theLastTrace


     set erreur [TCTL $property]

     if {$erreur == ""} {

	if {$optionTrace == 0} {set nbTrace 0}
	if {[peutOnChecker $fp]==1} {
            update idletasks
	    $fp.dialogue.retour.syntax insert end  "\n" 
	    $fp.dialogue.retour.syntax insert end  "$property \n" surgris
#	    if {$scheduling==1} {
#		$fp.dialogue.retour.syntax insert end  [mc "Cannot check property on Scheduling TPN (SETPN). \nProperty will be checked on the underlying TPN of the SETPN:\n"] bleu
	    #	    }
	    if {$typePN ==2} {
		$fp.dialogue.retour.syntax insert end  "Model checking not available for P-TPN\n" maron
	    } else {	
		$fp.dialogue.retour.syntax insert end  "Checking property $property on TPN: $nomCheck\n" maron
		$fp.dialogue.retour.syntax insert end  "Waiting for response (kill the romeo-cli process to interrupt)... \n" 
		update idletasks
		checkCTS $property
		afficheCheck $fp.dialogue.retour.syntax $nbTrace $optionSize
	    }
	}
	$fp.dialogue.retour.syntax yview moveto 1
	#   destroy $f
     } else {
	$fp.dialogue.retour.syntax insert end  "\n-------\n"
	$fp.dialogue.retour.syntax insert end  "Syntax error in property $property\n"
	$fp.dialogue.retour.syntax insert end  "$erreur" bleu
	$fp.dialogue.retour.syntax yview moveto 1
        update idletasks

     }
    }
  }
}

#++++++ procedures internes à check property



proc simulateTheTrace {w c} { 
    global firingSequence firingSequenceTotal
    global methode parameters typePN
    global theLastTrace
    global timedTrace 



    if {![winfo exists .fenetreSimul]} {
	simulateTPN $w $c
    }
    afficheSimu "\n"
    afficheSimu "-----------------------\n"
    afficheSimuColor "Importing Trace from model-checker\n" fondgris
    if {$timedTrace>0} {
	set firingSequence [detemporiseTrace $theLastTrace]
    } else {
	set firingSequence $theLastTrace
    }
    set firingSequenceTotal $firingSequence
    
    afficheSimuColor "Sequence from initial marking : $firingSequence\n" brown

    fireSequenceTransition $firingSequence
    redessinerRdP $c

    afficheDialogue .fenetreCheck "The initial marking has been changed by the simulator. Click on reset simulation button to reset to the initial marking.\n"
}

proc detemporiseTrace {chaine} { 
  set nextTime [nextSeparateur $chaine [list "@"]]
  set resultat ""

  while {([finLigne $chaine]==0)&&($nextTime>=0)} {
      set resultat $resultat[nextExpression $chaine "@"]
      set chaine [supNextExpression $chaine "@"]
      set nextVirgule [nextSeparateur $chaine [list ", "]]
      if {$nextVirgule>0} {
	  set resultat "$resultat, "
          set chaine [supNextExpression  $chaine ", "]
	  set nextTime [nextSeparateur $chaine [list "@"]]
      } else {
        set nextTime -1
      }  
  }
  return $resultat
}


proc afficheIndicePlace {fi} {
    global tabPlace 
    global tpn tabUnDo
    global fin
    global ok
    global infini

    text $fi.text -yscrollcommand "$fi.vscroll set" -setgrid true \
	-width 20 -height 8 -font fontEditor
    scrollbar $fi.vscroll -command "$fi.text yview"
    # -xscrollcommand "$fi.hscroll set"
    # scrollbar $fi.hscroll -orient horiz -command "$fi.text xview"


    pack $fi.vscroll -side right -fill y
    pack $fi.text -expand yes -fill both
    # pack $fi.hscroll -side bottom -fill x

    $fi.text tag configure rouge -foreground red
    $fi.text tag configure surgris -background #a0b7ce
    $fi.text tag configure souligne -underline on


    $fi.text insert end "  PLACE             \n" souligne
    $fi.text insert end "Index " surgris
    $fi.text insert end "  \"label\" \n" rouge


    # place par place
    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
	if {$tabPlace($tpn(courant),$i,statut)==$ok} {
	    $fi.text insert end "$i " surgris
	    $fi.text insert end "  \"$tabPlace($tpn(courant),$i,label,nom)\"\n" rouge
	}
    }
}
					       
#--------------------------------------------------------------------------------------------
# TCTL appelle expressionGMEC qui appelle GMEC qui appelle termeGMEC					     

#--------------------------------------------------------------------------------------------
proc termeGmec {chaine} {
    global tabPlace ok fin 
    global tpn tabUnDo
    global parameters

# optype = 0 pour rien, 1 pour operateur, 2 pour operande
set optype 0
set plusmoins 0
set erreur ""
 while {([finLigne $chaine]==0)&&($erreur=="")} {
      set chaine [gotonext $chaine]
      set sep [nextSeparateur $chaine [list + - * " " M( m( ( deadlock bounded markingBounded] ]  
# )))
      if {$sep > 0} {

         set plusmoins 0
	 if {$optype == 2} {
            set erreur "$chaine -> Operator expected"
         } else {
 	   set optype 2
           set erreur [verifOperande [string range $chaine 0 [expr $sep -1] ]]
           if {[finLigne $chaine]==0} {
             set chaine [gotonext [string range $chaine $sep [string length $chaine] ]]
	   }
         }
      } elseif {$sep ==0} {
          if {[carDansListe [nextCar $chaine]  [list M m]]} {
 	      if {$optype == 2} {
                  set erreur "$chaine -> Operator expected"
              } else {
		  set plusmoins 0
		  set optype 2
		  set fermePar [indexFinTerme [supNextCar $chaine]]
		  set erreur [verifMarking  [string range $chaine 0 [expr $fermePar+1] ]]    
		  set chaine [gotonext [string range $chaine [expr $fermePar+2] [string length $chaine]  ] ] 
              }
          } elseif {[carDansListe [nextCar $chaine]  [list + -]]} {
	      set optype 1
              incr plusmoins
	      if {$plusmoins < 2} {
                 set chaine [gotonext [supNextCar $chaine]]
		 if {[finLigne $chaine]} {set erreur "-> Bad expression"}
              } else {  set erreur "$chaine -> Bad expression"}
          } elseif {[nextCar $chaine]=="("} {
 		 if {$optype == 2} {
		     set erreur "$chaine -> Operator expected"
		 } else {
		     set plusmoins 0
		     set optype 2
		     set fermePar [indexFinTerme $chaine] 
		     if {$fermePar >=0} {
			 # ou etudie le terme en retirant les parentheses
			 set erreur [termeGmec [gotonext [string range $chaine 1 [expr $fermePar-1] ]] ]   
			 # et on continue avec la suite
			 set chaine [gotonext [string range $chaine [expr $fermePar+1] [string length $chaine]  ] ] 
		     } else {set erreur "$chaine -> missing close-brace"}
		 }
	  } elseif {[nextCar $chaine]=="*"} {
	      set plusmoins 0
	      if {$optype == 1} {
		  set erreur "$chaine -> Bad expression"
	      } else {
		 set optype 1
                 set chaine [gotonext [supNextCar $chaine]]
		 if {[finLigne $chaine]} {set erreur "$chaine -> Bad expression"}
	     }
	  } else {
# normalement inutil
            set chaine ""
          }
     } else {
          if {[finLigne $chaine]==1} {
            set erreur "$chaine -> Bad expression"
	  } else {
	      if {$optype == 2} {
                 set erreur "$chaine -> Operator expected"
              } else {
		  set erreur [verifOperande $chaine]
		  set chaine "" 
	      }
          }
      }
  }
 return $erreur
 }
#--------------------------------------------------------------------------------------------
proc GMEC {chaine} {
    global tabPlace ok fin
    global tpn tabUnDo
    global parameters

    set gauche ""
    set droite ""
    set erreur ""

    set sep [nextSeparateur $chaine [list > < == ! markingBounded bounded deadlock]]


# operateur binaire alors sep > 0 car operandes avant sep  et apres sep:
    if {$sep > 0} {
	if {[nextSeparateur $chaine [list >= <= == !=]]>0} {
	    set delta 2	    
	} else {
	    set delta 1
	}
	set gauche [gotonext [gotoprevious [string range $chaine 0 [expr $sep -1] ]]]
	set droite [gotonext [gotoprevious [string range $chaine [expr $sep+$delta] [string length $chaine] ]]]
    } else { set erreur "missing operator in GMEC $chaine" }



    if {[nbOccurence $gauche "("]-[nbOccurence $gauche ")"]!=[nbOccurence $droite ")"]-[nbOccurence $droite "("]} {
      set erreur "missing close-brace or extra characters after close-brace"
    } else {
	while {([nbOccurence $gauche "("]>[nbOccurence $gauche ")"]) && ($erreur == "")} {
	    if {([nextCar $gauche]=="(") && ([lastCar $droite]==")")} {
		set gauche  [gotonext [supNextCar $gauche]]
                set droite [gotoprevious [supLastCar $droite]]
	    } else { set erreur  "missing close-brace or extra characters after close-brace"}
	}
    }
    if {[finLigne $droite]||[finLigne $gauche]} {set erreur "-> Bad expression"}
    if {$erreur == ""} {
	set erreur [termeGmec $gauche]
    } 
    if {$erreur == ""} {
	set erreur [termeGmec $droite]
    } 


   return $erreur
}

#--------------------------------------------------------------------------------------------
proc expressionGMEC {chaine} {


set erreur ""
set optype 1

# optype = 0 pour rien, 1 pour operateurs and or =>, 2 pour GMEC, 3 pour not, (on considère que deadlock bounded est GMEC)

# Pas d'analyse pour le moment
return $erreur

 while {([finLigne $chaine]==0)&&($erreur=="")} {
     set chaine [gotonext $chaine]


# ICI c'est pour autoriser EF[0,100]( M(3)+ 2*( M(5) - 2*M(2) )  > 0 )
# On l'enleve car le parser de mercutio ne prend pas ca en compte
#     set sep [nextSeparateurSaufM $chaine [list not => and or AND OR] ]  
#     if {$sep <0 } {
#        set erreur [GMEC $chaine]
#        set chaine ""
#     } else {
#      }
#la fermeture est à mettre tout à la fin avant le return

       
#< #<= ICIC
     set sep [nextSeparateur $chaine [list \#< ]]
     if {$sep >=0} {
	 if {$sep < [nextSeparateur $chaine [list ( not => NOT and or AND OR markingBounded bounded deadlock M( m( A E ]]} {
	    set stepBound [nextExpressionListSep $chaine [list ( not => NOT and or AND OR markingBounded bounded deadlock M( m( A E]] 
	    set stepBound [gotonext [string range $stepBound [expr $sep+2] [string length $stepBound] ]]
	    if {[nextCar $stepBound]== "="} {set stepBound [supNextCar $stepBound]}						  
	    if {![entier [sansEspace $stepBound]]} {set erreur "$stepBound -> Integer expected"}
            set chaine [supBeforeListSep $chaine [list ( not => NOT and && or AND OR markingBounded bounded deadlock M( m( A E ]]
	 } else { set erreur "Bad setting of step bound"}
     }  

	 set sep [nextSeparateurSaufM $chaine [list ( not => NOT and or AND OR markingBounded bounded deadlock]]  
# )))
    if {$erreur == ""} {
	 if {$sep > 0} {
	     if {$optype == 2} {
		 set erreur "$chaine -> Operator (=>,and,or) expected"
	     } else {
		 set optype 2
		 set erreur [GMEC [gotonext [string range $chaine 0 [expr $sep -1] ]]]
		 if {[finLigne $chaine]==0} {
		     set chaine [gotonext [string range $chaine $sep [string length $chaine] ]]
		 }
	     }
	 } elseif {$sep ==0} {
	     if {[nextSeparateur $chaine [list deadlock] ]==0} {
 		 if {$optype == 2} {
		     set erreur "$chaine -> Operator (=>,not,and,or) expected"
		 } else {
		     set optype 2
		     set chaine [gotonext [string range $chaine 8 [string length $chaine] ]]
		 }
	     } elseif {[nextSeparateur $chaine [list deadlock markingBounded bounded] ]==0} {
 		 if {$optype == 2} {
		     set erreur "$chaine -> Operator (=>,not,and,or) expected"
		 } else {
		     set optype 2
		     if {[nextSeparateur $chaine [list markingBounded] ]==0} {
			 set chaine [supNextExpression $chaine "markingBounded"]
		     } else {
			 set chaine [supNextExpression $chaine "bounded"]
		     }
		     if {[entier [entreParentheses $chaine]]} {
			 set chaine [supNextExpression $chaine ")"]
		     } else {
			 set erreur "[entreParentheses $chaine] -> (integer) expected"
		     }
		 }
	     } elseif {[nextSeparateur $chaine [list => and or AND OR] ]==0} {
		 if {($optype==1)} {
		     set erreur "$chaine -> GMEC or deadlock or bounded(k) or markingBounded(k) expected"
		 } else {
		     set optype 1
		     if {([nextCar $chaine]=="o")||([nextCar $chaine]=="O")||([nextCar $chaine]=="=")} {
			 set chaine [gotonext [string range $chaine 2 [string length $chaine] ]]
		     } elseif {
			       ([nextCar $chaine]=="a")||([nextCar $chaine]=="A")} {set chaine [gotonext [string range $chaine 3 [string length $chaine] ]]
		     }
		     if {[finLigne $chaine]} {set erreur "-> GMEC expected"}
		 }
	     } elseif {[nextSeparateur $chaine [list not NOT] ]==0} {
		 if {($optype!=1)} {
		     set erreur "$chaine -> Operator (=>,not,and,or) expected"
		 } else {
		     set optype 3
		     set chaine [gotonext [string range $chaine 3 [string length $chaine] ]]
		     if {[finLigne $chaine]} {set erreur "-> GMEC expected"}
		 }	     
	     } elseif {[nextCar $chaine]=="("} {
 		 if {$optype == 2} {
		     set erreur "$chaine -> Operator (=>,not,and,or) expected"
		 } else {
		     set optype 2
		     set fermePar [indexFinTerme $chaine] 
		     if {$fermePar >=0} {
			 # ou etudie le terme en retirant les parentheses
			 set erreur [expressionGMEC [gotonext [string range $chaine 1 [expr $fermePar-1] ]] ]   
			 # et on continue avec la suite
			 set chaine [gotonext [string range $chaine [expr $fermePar+1] [string length $chaine]  ] ] 
		     } else {set erreur "$chaine -> missing close-brace"}
		 }
	     }
	 } else {
	     if {[finLigne $chaine]==1} {
		 set erreur "$chaine -> Bad expression"
	     } else {
		 if {$optype == 2} {
		     set erreur "$chaine -> Operator (=>,not,and,or) expected"
		 } else {
		     set erreur [GMEC [gotonext  $chaine]]
		     set chaine "" 
		 }
	     }
	 }
      }
    }
 return $erreur
 }


proc faireListeMarkingBounded {infeqTheBound} { 
  global tabPlace ok fin
  global tpn projet nbTokenColor

    
    set leOnglet [numOnglet $tpn(courant)]
    set bornitude ""
    set coma ""

    if {$nbTokenColor($tpn(courant))>0} {

	for {set laCouleur 0} {$laCouleur< $nbTokenColor($tpn(courant))} {incr laCouleur} {

	    for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
		if {$tabPlace($tpn(courant),$i,statut)==$ok} {
		    set bornitude "$bornitude $coma $tabPlace($tpn(courant),$i,id)\[$laCouleur\]$infeqTheBound"
		    set coma "and"
		}
	    }
	    
	    for {set i 1} {$i<=$projet($leOnglet,nbInput)}  {incr i} {
		if {$projet($leOnglet,input,$i,status) != "deleted"} {
		    set prefixe "[sansXml $projet($tpn(onglet),input,$i,file)]::"
		    set leSlave [calculTPNCourant $i]
		    for {set j 1} {$tabPlace($leSlave,$j,statut)!=$fin} {incr j} { 
			if {$tabPlace($leSlave,$j,statut)==$ok} { 
			    set bornitude "$bornitude $coma $prefixe$tabPlace($leSlave,$j,id)\[$laCouleur\]$infeqTheBound"
			    set coma "and"
			} 
		    }	
		}
	    }
	}
     
 } else { # Si pas de ccouleur
     
         for {set i 1} {$tabPlace($tpn(courant),$i,statut)!=$fin} {incr i} {
	if {$tabPlace($tpn(courant),$i,statut)==$ok} {
	 set bornitude "$bornitude $coma $tabPlace($tpn(courant),$i,id)$infeqTheBound"
	 set coma "and"
	}
     }

    for {set i 1} {$i<=$projet($leOnglet,nbInput)}  {incr i} {
	if {$projet($leOnglet,input,$i,status) != "deleted"} {
	    set prefixe "[sansXml $projet($tpn(onglet),input,$i,file)]::"
	    set leSlave [calculTPNCourant $i]
	    for {set j 1} {$tabPlace($leSlave,$j,statut)!=$fin} {incr j} { 
		if {$tabPlace($leSlave,$j,statut)==$ok} { 
		    set bornitude "$bornitude $coma $prefixe$tabPlace($leSlave,$j,id)$infeqTheBound"
		    set coma "and"
	   	} 
	    }	
	}
    }
 }
    return "$bornitude"
}

#--------------------------------------------------------------------------------------------
# remplacer M(i) par labelPlace'Pi
#--------------------------------------------------------------------------------------------
proc calculPropCTS {chaine} {
  global tabPlace ok fin
  global tpn tabUnDo
  global parameters

  set resultat ""
  set nextM [nextSeparateur $chaine [list "M("]]
 
  while {([finLigne $chaine]==0)&&($nextM>=0)} {
    set resultat $resultat[nextExpression $chaine "M("]
    set chaine [supNextExpression $chaine "M("]
    set indice [nextExpression $chaine  ")"]
    set chaine [supNextExpression  $chaine ")"]

    set nextM [nextSeparateur $chaine [list "M("]]
    set resultat  $resultat$indice
#    set resultat  $resultat[sansEspace $tabPlace($tpn(courant),$indice,label,nom)]'P$indice
  }
  set resultat "$resultat$chaine"

 if {[nextSeparateur $resultat [list "markingBounded("]]>=0} {
     set chaine [supNextExpression $resultat "markingBounded("]
     set infeqTheBound "<="
     set infeqTheBound $infeqTheBound[nextExpression $chaine ")"]
     set bornitude ""
     set coma ""
     set bornitude "([faireListeMarkingBounded $infeqTheBound])"

     set resultat [nextExpression $resultat "markingBounded("]$bornitude[supNextExpression $chaine ")"]
 }

  return $resultat
 
}

#--------------------------------------------------------------------------------------------
proc TCTL {chaine} {
    global tabPlace ok fin
    global tpn tabUnDo
    global parameters cost controle
    set erreur ""
#    set chaine [sansEspace $chaine]
    set chaine [gotonext $chaine]

 if {[nextSeparateur $chaine [list "control" "avoid" ]]==0} {
     if {$controle==0} {
	 set erreur "Not allowed. Control PN not selected"
     } else {
	 if {[nextSeparateur $chaine [list "control"]]==0} {
	     set chaine [gotonext [supNextExpression $chaine "control"]]
	 } else {
	     set chaine [gotonext [supNextExpression $chaine "avoid"]]
	 }

	 set chaine [entreParenthesesGeneral $chaine]	
	 if {[nextSeparateur $chaine [list " U "]]==-1} {
	     set erreur [expressionGMEC $chaine]
	 } else {
	     set erreur [expressionGMEC [nextExpression $chaine " U "]]
	     if {$erreur == ""} {
		 set erreur [expressionGMEC [supNextExpression $chaine " U "]]
	     }
	 }
     }
  } elseif {[nextSeparateur $chaine [list "mincost" ]]==0} {

     if {$cost<1} {
	 set erreur "Cost TPN not selected"
     } else {
	 set chaine [gotonext [supNextExpression $chaine "mincost"]]

	 set chaine [entreParenthesesGeneral $chaine]	
	 if {[nextSeparateur $chaine [list " U "]]==-1} {
	     set erreur [expressionGMEC $chaine]
	 } else {
	     set erreur [expressionGMEC [nextExpression $chaine " U "]]
	     if {$erreur == ""} {
		 set erreur [expressionGMEC [supNextExpression $chaine " U "]]
	     }
	 }
     }
 } else {
     if {[nextSeparateur $chaine [list "not"]]==0} {
	 set chaine [gotonext [supNextExpression $chaine "not"]]
     }
     if {[nextSeparateur $chaine [list "E" "A" ]]==0} {
	set EA [nextCar $chaine]                        
# on supprime l'espace entre EA et (FG
	set chaine [gotonext [supNextCar $chaine]]
	set chaine $EA$chaine
    }
    if {[nextSeparateur $chaine [list "E(" "EF" "A(" "AF" "EG" "AG" " U " "maxv" "minv" "when" "while" "maxc" "minc"]]==0} { 
	set quantif [string range $chaine 0 1]
#	set sep [nextSeparateur $chaine [list "E(" "EF" "A(" "AF" "EG" "AG" ]]
	switch $quantif {
	    "E(" {
	          set fermePar [indexFinTerme [supNextCar $chaine]]
		  set erreur [expressionGMEC  [string range $chaine 1 [expr $fermePar+1] ]]    
		  set chaine [gotonext [string range $chaine [expr $fermePar+2] [string length $chaine]  ] ] 
		  if {$erreur == ""} {
		      set erreur [until $chaine]
		  }
	    }
	    "A(" {
	          set fermePar [indexFinTerme [supNextCar $chaine]]
		  set erreur [expressionGMEC  [string range $chaine 1 [expr $fermePar+1] ]]    
		  set chaine [gotonext [string range $chaine [expr $fermePar+2] [string length $chaine]  ] ] 
		  if {$erreur == ""} {
		      set erreur [until $chaine]
		  }
	    }
	    default {
		  set erreur [afterUntil  [string range $chaine 2 [string length $chaine] ]]    
	    }
        }
    } elseif {[string first "-->" $chaine]>0} {
	set erreur  [expressionGMEC [string range $chaine 0 [expr [string first "-->" $chaine]-1] ]]
       if {$erreur == ""} {
	   set erreur [afterUntil [string range $chaine [expr [string first "-->" $chaine]+3] [string length $chaine]  ]]
       }

    } else {
	set erreur "$chaine -> Bad expression"
    }
  }
  return $erreur
}

#--------------------------------------------------------------------------------------------
proc until {chaine} {

set erreur ""

    if {[nextCar $chaine]!="U"} {
      set erreur "$chaine -> U expected"
    } else {
	set erreur [afterUntil [supNextCar $chaine]]
    }
return $erreur
}

proc afterUntil {chaine} {
    global parameters

    set erreur ""
    set chaine [gotonext $chaine]
    if {[nextCar $chaine] == "\["} {
	set interval [nextExpression [supNextExpression $chaine "\["]  "\]"]
	set suite [supNextExpression $chaine "\]"]
	if {$parameters==0} {
	    set nb1 [nextExpression $interval ","]
	    set nb2 [supNextExpression $interval ","]
	    if {!([entier $nb1] && ([entier $nb2] || ([sansEspace $nb2] =="inf") ))} {          
		set erreur "\[$nb1,$nb2\] -> integer or inf expected"
	    } 
	}
    } else {
	set suite $chaine
    }
    if {$erreur == ""} {
	set erreur [expressionGMEC $suite]
    }
    
   return $erreur
}

proc verifOperande {chaine} {

# todo verifier que c'est bien une operande : entier ou parametre

#    if {![entier $chaine]} { 
#	set erreur "$chaine -> integer expected"
 #   } else { 
#	set erreur ""
 #   }
	set erreur ""

return $erreur
}

proc verifMarking {chaine} {

   global tabPlace ok fin
    global tpn tabUnDo
   global parameters

set erreur ""
    # on commence par calculer l'indice max des places
    for {set iMax 1} {$tabPlace($tpn(courant),$iMax,statut)!=$fin} {incr iMax} {}

   # extraire indice : M(indice)
    set identifier [nextExpression [supNextExpression $chaine "("]  ")"] 

    if {[existIdP $tpn(courant) $identifier]==0} {
	      set erreur "M($identifier) error ->  $identifier : place identifier expected"
    }
return $erreur
}


proc entreParentheses {chaine} {
   set indexCar 0
   set openClose 1

   set resul ""
   if {[nextCar $chaine]== "("} { 
       # retirer l'ouverture de parenthese
       set chaine [supNextCar $chaine] 
       if {[finLigne $chaine] ==0} {
	   set firstPosition [string first ")" $chaine]
	   if {$firstPosition >=0} {
	       set resul [string range $chaine 0 [expr $firstPosition -1] ]
	   } else { 
	       set resul "missing open or close-brace" 
	   }
       }
   } else {
      set resul "missing parenthesis" 
   }

   return $resul
}



proc entreParenthesesGeneral {chaine} {

   set resul ""
    set chaine [gotonext $chaine]
    if {[nextCar $chaine]== "("} { 
       set fermePar [indexFinTerme $chaine]
	set resul  [string range $chaine 1 [expr $fermePar-1]]    
   } else {
       set resul $chaine
   }
   return $resul
}


proc indexFinTerme {chaine} {
   set indexCar 0
   set openClose 1

 # retirer l'ouverture de parenthese
   set chaine [supNextCar $chaine] 
   while {([finLigne $chaine]==0)&&($openClose>0)} {
       if {[nextCar $chaine] == ")"} {
          set openClose [expr $openClose-1]
       } elseif {[nextCar $chaine] == "("} {
          incr openClose
       }
       set chaine [supNextCar $chaine]
       incr indexCar
   }

   if {([finLigne $chaine]==1)&&($chaine>0)} {
      return -1
   } else { return $indexCar}

}


proc entreAccolade {chaine} {

   set resul ""
    set chaine [gotonext $chaine]
   if {[nextCar $chaine]== "\{"} { 
       set fermeAccol [indexFermetureAccolade $chaine]
	set resul  [string range $chaine 1 [expr $fermeAccol-1]]    
   } else {
       set resul $chaine
   }
   return $resul
}


proc indexFermetureAccolade {chaine} {
   set indexCar 0
   set openClose 1

 # retirer l'ouverture de l'accolade
   set chaine [supNextCar $chaine] 
   while {([finLigne $chaine]==0)&&($openClose>0)} {
       if {[nextCar $chaine] == "\}"} {
          set openClose [expr $openClose-1]
       } elseif {[nextCar $chaine] == "\{"} {
          incr openClose
       }
       set chaine [supNextCar $chaine]
       incr indexCar
   }

   if {([finLigne $chaine]==1)&&($chaine>0)} {
      return -1
   } else { return $indexCar}

}
		

#--------------------------------------------------------------------------------------------

proc nbOccurence {chaine leCaractere} {
   set nombre 0
   while {([finLigne $chaine]==0)} {
     if {[nextCar $chaine] == $leCaractere} {incr nombre}
     set chaine [supNextCar $chaine]
   }
   return $nombre
}

proc xmlProperty {indice comp val} {

    switch $comp {
	>  { set op "Greater" }
	<  { set op "Lower"  }
	>= { set op "GreaterOrEqual" }
	<= { set op "LowerOrEqual"   }
	=  { set op "Equal"   }
	default {
	    set op ERREUR
	    #     puts $comp
	}
    }
    return "    <place id=\"$indice\" op=\"$op\" value=\"$val\"\/>\n"
}


proc supNextExpression {chaine separateur} {
    set resul ""
    if {[finLigne $chaine] ==0} {
	set firstPosition [string first $separateur $chaine]
	if {$firstPosition >=0} {set resul [string range $chaine [expr $firstPosition + [string length $separateur]] [string length $chaine] ]
	} else { set resul "" }
    }
    return $resul
}


proc existCarDansMot {mot separateur} {
    set firstPosition [string first $separateur $mot]
    if {$firstPosition >=0} { 
	return 1
      } else {
	  return 0
      }
}

proc nextExpression {chaine separateur} {
    set resul ""
    if {[finLigne $chaine] ==0} {
	set firstPosition [string first $separateur $chaine]
	if {$firstPosition >=0} {set resul [string range $chaine 0 [expr $firstPosition -1] ]
	} else { set resul $chaine }
    }
    return $resul
}

proc occurence {chaine numOccurence separateur} {
    set resul ""
    set pointeur 0
    for {set i 1} {$i<$numOccurence} {incr i} {
	set pointeur [expr $pointeur+[string length [nextExpression $chaine $separateur]]+1]
	set chaine [supNextExpression $chaine $separateur]
    }
    
    return [expr $pointeur+[string length [nextExpression $chaine $separateur]]]

}

proc supBeforeListSep {chaine listeSeparateur} {
    set resul ""
    if {[finLigne $chaine] ==0} {
	set sep [nextSeparateur $chaine $listeSeparateur]  
#puts "$listeSeparateur sep -> $sep"
	if {$sep >=0} { set resul [gotonext [string range $chaine $sep [string length $chaine] ]]
	} else { set resul ""}
     } else { set resul "" }
    
    return $resul
}


proc nextExpressionListSep {chaine listeSeparateur} {
    set resul ""
    if {[finLigne $chaine] ==0} {
	set sep [nextSeparateur $chaine $listeSeparateur]
	if {$sep >=0} {
	    set resul [string range $chaine 0 [expr $sep -1] ]
	} else {
	    set resul $chaine
	}
     } else { 
	 set resul "" 
     }
    
    return $resul
}



proc finLigne {chaine} {
    set fin 1
    for {set i 0} {[string index $chaine $i] != ""}   {incr i} {
	if {[string compare [string index $chaine $i] " "]!=0} {set fin 0}
    }
    return $fin
}


proc entier {chaine} {
    set resul 1
    if {[string compare $chaine ""]==0} {set resul 0}
    while {[string compare $chaine ""]} {
	if {[nextCar $chaine] == " "}{set chaine [supNextCar $chaine]}
	if {[string compare $chaine ""]==0} {set resul 0}
    }
    while {[string compare $chaine ""]} {
	if {[string first [nextCar $chaine] "0123456789"]<0} {set resul 0}
	set chaine [supNextCar $chaine]
    }
    return $resul
}

proc flottant {chaine} {
    set resul 1
    if {[string compare $chaine ""]==0} {set resul 0}
    while {[string compare $chaine ""]} {
	if {[string first [nextCar $chaine] "0123456789."]<0} {set resul 0}
	set chaine [supNextCar $chaine]
    }
    return $resul
}


proc nextCar {chaine} {

    if {[string compare $chaine ""]} {
	return [string index $chaine 0]
    } else { return ""}

}

proc supNextCar {chaine} {
    if {[string compare $chaine ""]} {
	return [string range $chaine 1 [string length $chaine] ]
    } else {  return ""}
}

proc lastCar {chaine} {

    if {[string compare $chaine ""]} {
	return [string index $chaine  [expr [string length $chaine]-1]]
    } else { return ""}

}
proc supLastCar {chaine} {
    if {[string compare $chaine ""]} {
	return [string range $chaine 0 [expr [string length $chaine]-2]]
    } else {  return ""}
}

#string index string charIndex
#Returns the charIndex'th character of the string argument.  A charIndex of 0 corresponds to the first character of the string. If charIndex is less than 0 or greater than or equal to the length of the string then an emptfinLigney string is returned.
#[string last "/" $fichier]
#[string compare $nomRdP "noName.xml"]
#set nomProcedure [string range $fichier [expr $dernierSlach + 1] [string length $fichier] ]
#set espace [string first "/" $phrase]


# A SUPPRIMER
proc supNextMot {chaine} {
    set chaine [gotonext $chaine]
    set resul ""
    if {[finLigne $chaine] ==0} {
	set firstEspace [minPlus [minPlus [string first "!" $chaine] [string first ">" $chaine]] \
			     [minPlus [minPlus [string first " " $chaine] [string first ";" $chaine]] \
                                  [minPlus [string first ")" $chaine] [string first "(" $chaine]] ] ]
	if {$firstEspace>=0} {set resul [string range $chaine [expr $firstEspace] [string length $chaine] ]
	} else { set resul $chaine }
    }
    return [gotonext $resul]
}



# enleve les espaces en debut de chaine
proc gotonext {chaine} {
    set x 0
    while {([string index $chaine $x] == " ")||([string index $chaine $x] == "\n")} {incr x}
    return [string range $chaine $x [string length $chaine] ]
}

proc gotoprevious {chaine} {
    set x  [expr [string length $chaine] - 1]
    while {[string index $chaine $x] == " "} {set x [expr $x-1]}
    return [string range $chaine 0 $x]
}



proc nextMot {chaine} {
    set resul ""
    set chaine [gotonext $chaine]
    if {[finLigne $chaine] ==0} {
	set firstEspace [minPlus [minPlus [string first "!" $chaine] [string first ">" $chaine]] \
			     [minPlus [minPlus [string first " " $chaine] [string first ";" $chaine]] \
                                  [minPlus [string first ")" $chaine] [string first "(" $chaine]] ] ]
	if {$firstEspace>=0} {set resul [string range $chaine 0 [expr $firstEspace -1] ]
	} else { set resul $chaine }
    }
    return $resul
}

proc minPlus {a b} {
    if {$a<0} {set a $b}
    if {$b<0} {set b $a}
    if {$a <$b} {return $a} else {return $b}
}


#************************************************************************************
# Verification syntaxique des contraintes

proc carDansListe {caractere liste} {
    set reponse 0

    for {set i 0} {$i<[llength $liste]} {incr i} {
	if {$caractere == [lindex $liste $i]} {set reponse 1}
    }
    return $reponse
}

proc nextSeparateur {chaine listeSeparateur} {
    set theFirst -1
    for {set i 0} {$i<[llength $listeSeparateur]} {incr i} {
	set theFirst [minPlus $theFirst [string first [lindex $listeSeparateur $i] $chaine]]
    }
 #   puts $theFirst
    return $theFirst
}

proc quelEstNextSeparateur {chaine listeSeparateur} {
    set theFirst -1
    set theNewFirst -1
    set resul ""
    for {set i 0} {$i<[llength $listeSeparateur]} {incr i} {
	set theNewFirst [minPlus $theNewFirst [string first [lindex $listeSeparateur $i] $chaine]]
	if {($theNewFirst < $theFirst)||(($theFirst<0)&&($theNewFirst >=0))} {
	    set resul [lindex $listeSeparateur $i]
	    set theFirst $theNewFirst
	}
    }
 #   puts $theFirst
    return $resul
}

proc retirerListeSeparateur {chaine listeSeparateur} { 

#    set chaine [string map {== "" >= ""} $chaine]

    set sep [nextSeparateur $chaine $listeSeparateur]
    while {$sep >-1} {
	set concatGauche [string range $chaine 0 [expr $sep -1]] 
	set concatDroite [string range $chaine [expr $sep + [string length [quelEstNextSeparateur $chaine $listeSeparateur]]] [string length $chaine] ]
	set chaine "$concatGauche$concatDroite" 
	set sep [nextSeparateur $chaine $listeSeparateur]
     } 
  return $chaine 
} 
 


proc nextSeparateurSaufM {chaine listeSeparateur} {
    set chaine [string map {M( MM m( mm} $chaine]
   return  [nextSeparateur $chaine $listeSeparateur]
}


proc verifSyntaxeParametre {chaine} {
set erreur ""
set operande1 ""
set operateur ""
set plusmoins 0

  set chaine [gotonext $chaine]
  while {([finLigne $chaine]==0)&&($erreur=="")} {
      set sep [nextSeparateur $chaine [list + - * / " "]]
      if {$sep > 0} {
         set plusmoins 0
         set operande1 [string range $chaine 0 [expr $sep -1] ]
         if {[finLigne $chaine]==0} {
           set chaine [gotonext [string range $chaine $sep [string length $chaine] ]]
           set operateur [nextCar $chaine]
	   if {[carDansListe $operateur  [list + - * /]]} {
               set chaine [gotonext [supNextCar $chaine]]
 	       if {[finLigne $chaine]} {set erreur "$operande1$operateur... Error -> parameter or integer expected"}
	   } elseif {![finLigne [gotonext $chaine]]} {
	      set erreur "$operande1... Error -> Operator expected"
           }
	 }
      } elseif {$sep ==0} {
          if {[carDansListe [nextCar $chaine]  [list + -]]} {
             incr plusmoins
	      if {$plusmoins < 2} {
                 set chaine [gotonext [supNextCar $chaine]]
              } else {  set erreur "$chaine Bad expression"}
          } else {
             set erreur "$chaine... Error -> parameter or integer expected"
	  }
      } else {
          if {[finLigne $chaine]==1} {
            set erreur "$chaine Bad expression"
	  } else {set chaine "" }
      }
  }
 return $erreur 
}


proc verifSyntaxeContrainte {chaine} {
set erreur ""
#set operande1 ""
set operateur ""
set comparDone 0
set sep 0

#  set chaine [sansEspace $chaine]
    if {[string first "=" [retirerListeSeparateur $chaine  [list "*" / >= > <= < == !=]]]>-1} {
	set erreur "Found \"=\" instead of \"==\""
  }


  while {([finLigne $chaine]==0)&&($erreur=="")&&($sep>-1)} {
      set sep [nextSeparateur $chaine [list +  "*" / >= > <= < == !=]]
#      set operande1 [string range $chaine 0 [expr $sep -1] ]
      set operateur  [quelEstNextSeparateur $chaine [list + -  "*" /  "<<"  ">>" >= > <= < == !=]]
      set chaine  [gotonext [string range $chaine [expr $sep  + [string length $operateur]] [string length $chaine] ]]
      if {$sep > 0} {
	 if {[finLigne $chaine]==1} {set erreur "$chaine -> Bad expression"}
	 if {$operateur != "*"} {
	      if {[lsearch [list >= > <= < == !=] $operateur]>-1} {incr comparDone}
	 }
	 if {$comparDone>1} {set erreur "$chaine... -> Bad expression"}
      } elseif {$sep ==0} {
	  set erreur "$chaine -> Bad expression"
      }
  }
# puts $erreur
 return $erreur
}



proc afficheGrammaire {f1} {
    global scheduling parameters typePN cost controle


    $f1.syntax tag configure maron -foreground brown
    $f1.syntax tag configure rouge -foreground red
    $f1.syntax tag configure vert -foreground darkgreen
    $f1.syntax tag configure bleu -foreground darkblue
    $f1.syntax tag configure surgris -background #c0d7ee

    $f1.syntax insert end "GMEC" surgris
    $f1.syntax insert end " = a * M(Pi) \{+,-\} b * M(Pj) \{<, <=, >, >=, ==, !=\} k \| deadlock \| bounded(k) \| markingBounded(k) \| p and q \| p or q \| p => q \| not p \n" bleu
    $f1.syntax insert end [mc "M: keyword (marking); deadlock, bounded, markingBounded: keywords; Pi,Pj: place identifier; a,b,k: integer ; *, +, -, and, or, =>, not: usual operator ; p,q: GMEC \n "]
    $f1.syntax insert end "Pi can also be used as a shorthand of M(Pi) \n \n"

    # typePN -> -1 : stopwatch ;   -2 scheduling ; 1 t-tpn ; 2 p-tpn

  if {$typePN == 2} {
        $f1.syntax insert end "pTPN-CTL" surgris
	$f1.syntax insert end " = E (p)U(q) \| A (p)U(q) \| EF (p) \| A F(p) \| EG (p) \| AG (p) \| EF (p) \| (p)-->(q) \| phi and psi \| phi or psi \n" bleu
        $f1.syntax insert end [mc "p,q: GMEC; phi, psi : pTPN-CTL; U: until; E: exists; A: forall; F: eventually; G: always; --> : response. \n"]

  } elseif {$controle>=1} {
        $f1.syntax insert end "Control formulae " surgris
        $f1.syntax insert end " =  control (p) \| control (p) U (q) | avoid (p)     " bleu
        $f1.syntax insert end " with p,q: GMEC. \n\n"
	$f1.syntax insert end "Example 1" surgris
	$f1.syntax insert end ": control (Goal==1)" bleu 
	$f1.syntax insert end " asks if there exists a winning memoryless strategy for the controller allowing to reach a state such that Goal==1.
The strategy of the controller is given. \n\n"
	$f1.syntax insert end "Example 2" surgris
	$f1.syntax insert end ": avoid (BAD==1)" bleu
	$f1.syntax insert end " asks if there exists a winning memoryless strategy for the controller allowing to avoid a state such that BAD==1 without deadlocking. \nIt means that if the environment can block the system then the controller loses even if BAD is avoided. \nThe strategy of the environment is given but not that of the controller. \n"
  } else {
	if {$parameters>=1} {
	    $f1.syntax insert end "ParamTPN-PTCTL" surgris
	    $f1.syntax insert end " = E(p)U\[a,b\](q) \| A(p)U\[a,b\](q) \| EF\[a,b\](p) \| AF\[a,b\](p) \| EG\[a,b\](p) \| AG\[a,b\](p) \| EF\[a,b\](p) \| (p)-->\[0,b\](q)  \n" bleu
	    $f1.syntax insert end [mc "p,q: GMEC; U: until; E: exists; A: forall; F: eventually; G: always; --> : response; a: parameter or integer; b parameter or integer or \{inf\} \n"]
	} else {
	    $f1.syntax insert end "TPN-TCTL" surgris
	    $f1.syntax insert end " = E (p)U\[a,b\](q) \| A (p)U\[a,b\](q) \| EF\[a,b\] (p) \| AF\[a,b\] (p) \| EG\[a,b\] (p) \| AG\[a,b\] (p) \| EF\[a,b\] (p) \| (p)-->\[0,b\] (q)  \n" bleu
	    $f1.syntax insert end [mc "p,q: GMEC; U: until; E: exists; A: forall; F: eventually; G: always; --> : response; a: integer; b integer or \{inf\} \n"]
	}
	# T-TPN et parametric :
	$f1.syntax insert end [mc "A missing interval is equivalent to \[0,inf\]  \n"]
	$f1.syntax insert end [mc "\nThe syntax (p)-->\[0,b\](q) denotes a leads to property meaning AG( (p) imply AF\[0,b\](q) ). E.g. (p)-->\[0,b\] (q) holds if and only if whenever p holds eventually q will hold as well in \[0,b\] time units. \n \n"]


      if {$cost == 0} {
	$f1.syntax insert end  "Step Bound" surgris
	$f1.syntax insert end ": the maximal size (N) of discrete runs can by specify by adding "
 	$f1.syntax insert end "\#<=N" bleu  
 	$f1.syntax insert end " or "  
	$f1.syntax insert end "\#<N" bleu  
 	$f1.syntax insert end " after the time interval where N is a positive integer.\n \n"

	$f1.syntax insert end "Example 1" surgris
	$f1.syntax insert end ": EF\[0,10\](M(P2)-M(P3)>0)" bleu
	$f1.syntax insert end " or briefly" 
	$f1.syntax insert end " EF\[0,10\](P2 - P3 >0)" bleu
	$f1.syntax insert end " means that a state with a marking M such that M(P2)-M(P3)>0 (where P2 and P3 are places of the net) is reachable in less than 10 time units.\n"
	$f1.syntax insert end "Example 2" surgris
	$f1.syntax insert end ": A\[0,20\]  (P2==1) U (P3>2) " bleu
	$f1.syntax insert end " means that  for all runs of less than 20 time units, there is a token in P2 until there are more than 2 tokens in P3.\n"
	$f1.syntax insert end "Example 3" surgris
	$f1.syntax insert end ": AG\[0,inf\](not deadlock) and (bounded(3))" bleu
	$f1.syntax insert end " means that the TPN has no deadlock and is 3-bounded (markings and variables).\n"
	$f1.syntax insert end "Example 4" surgris
	$f1.syntax insert end ": AG (markingBounded(1))" bleu
	$f1.syntax insert end " means that the TPN is 1-bounded (safe markings).\n"
	$f1.syntax insert end "Example 5" surgris
	$f1.syntax insert end ": AG\[0,inf\]\#<=3 (not deadlock)" bleu
	$f1.syntax insert end " means that the TPN cannot reach a deadlock within 3 steps."

      }	else {
#    if {$cost > 0} 
	    $f1.syntax insert end "\n --------------------\n \n"

        $f1.syntax insert end  "Cost (Priced) TPN \n 1)" surgris
        $f1.syntax insert end  "  EF (goal and cost <= k)" bleu
        $f1.syntax insert end  "  where goal is given by GMEC and k is an integer -> check if goal is reachable with cost <= k.\n"
	    if {$parameters>=1} {
	        $f1.syntax insert end  "In parametric mode, synthesise the parameter values such that the property is true.\n"
	    } 
	    $f1.syntax insert end  " 2)" surgris
	    $f1.syntax insert end  "  mincost(goal)" bleu
	    $f1.syntax insert end  " -> Find the minimal cost to reach a goal state given by a GMEC \n"
	    if {$parameters>=1} {
	        $f1.syntax insert end  "In parametric mode, synthesise the parameter values such that the minimal cost is realisable.\n"
        }
	    $f1.syntax insert end  " 3)" surgris
	    $f1.syntax insert end  "  mincost (property) U (goal)" bleu
	    $f1.syntax insert end  "  where property and goal are given by GMEC -> Find the minimal cost to reach goal while property remains true until goal is reached.\n"
	    if {$parameters>=1} {
	        $f1.syntax insert end  "In parametric mode, synthesise the parameter values such that the minimal cost is realisable.\n"
	    }
        $f1.syntax insert end  "\n Ex1:"
        $f1.syntax insert end  " EF (p3==2 and cost <= 10)" bleu
        $f1.syntax insert end  " check if (p3==2) is reachable whith a cost lower than 10. \n" 

	    $f1.syntax insert end  " Ex2: " 
	    $f1.syntax insert end  "mincost (p3 == 0)" bleu
	    $f1.syntax insert end  "  or  " 
	    $f1.syntax insert end  "mincost (M(p3) == 0)" bleu
	    $f1.syntax insert end  "  Find the minimal cost to reach (M(p3) == 0) \n" 
	    
        $f1.syntax insert end  " Ex3: " 
	    $f1.syntax insert end  "mincost (markingBounded(1)) U (p3 == 0)" bleu
	    $f1.syntax insert end  "  Find the minimal cost to reach (M(p3) == 0) by a sequence such that markingBounded(1) is true \n \n" 
    } 
  }
  $f1.syntax insert end "\n --------------------\n \n"
#    if {$scheduling} {
#	$f1.syntax insert end [mc "Scheduling mode is selected"] surgris
#	$f1.syntax insert end "\n\n       -> "
#	$f1.syntax insert end [mc "Property will be costed on underlying TPN"] rouge
#	$f1.syntax insert end "\n          ------------------------------------------\n " bleu
#    }

}


proc arroundError {numLineError chaine} {

    set numLine 1
    set avecNumLigne ""
    if {[numberOfLines $chaine] >15} {
	set numMin [expr $numLineError -4]
	set numMax [expr $numLineError +8]
    } else {
	set numMin 1
	set numMax [expr [numberOfLines $chaine]+1]
    }
    while {([string compare $chaine ""])&&($numLine<=$numMax+1)} {
	if {($numLine>=$numMin)&&($numLine<=$numMax)} {
	    set avecNumLigne "$avecNumLigne$numLine [nextExpression $chaine "\n"]\n"
	}
	set chaine [supNextExpression $chaine "\n"]
	incr numLine
    }
 
return $avecNumLigne
}

proc arroundErrorFromCTS {numLineError ctsfile} {
    puts $ctsfile

    set file [open $ctsfile r]
    set  affArround  ""

    for {set i 1} {($i<$numLineError+5) && ![eof $file]}  {incr i} {
	set line [gets $file]
	if {($i> $numLineError-5)} {
	    set affArround "$affArround $i  : $line \n"
	}
    }
    close $file
 
    return $affArround
}


proc verifSyntaxeGarde {chaine} {

set listeSeparateur  [list and or "&&" "&" "||" "|" "=>" not]
set erreur ""
   set sep [nextSeparateur $chaine $listeSeparateur]
    while {($sep >-1)&&($erreur=="")} {
	set contrainteGauche [string range $chaine 0 [expr $sep -1]] 
	set chaine [string range $chaine [expr $sep + [string length [quelEstNextSeparateur $chaine $listeSeparateur]]] [string length $chaine] ]
	set sep [nextSeparateur $chaine $listeSeparateur]
	set erreur [verifSyntaxeContrainte $contrainteGauche]
    } 
    if {$erreur==""} {
	set erreur [verifSyntaxeContrainte $chaine]
    }
    return $erreur 
} 


proc verifSyntaxeUpdateAtomique {chaine} {

set erreur ""
   if {([nextSeparateur $chaine  [list > < ==]]> -1)&&([nextSeparateur $chaine  [list >> <<]]< 0)} {
	set erreur "Found [quelEstNextSeparateur $chaine  [list > < ==]] in $chaine"
   } else {
       if {([nextSeparateur $chaine  [list =]]> -1)} {
	   set laVariable [nextExpression $chaine "="]
	   set lexpression [supNextExpression $chaine "="]

	   if {[nextSeparateur $laVariable [list + - "*" /]]>-1} {
	       set erreur "Found [quelEstNextSeparateur $chaine [list + - "*" /]] in $laVariable"
	   } elseif {[nextSeparateur [sansEspace $lexpression] [list ++ -- -+ +- "-*" "+*" "*-" "*+" +/ -/ "/*" "*/" /+ /- "**" "//" =]]>-1} {
	       set erreur "Found [quelEstNextSeparateur [sansEspace $lexpression] [list ++ -- -+ +- "-*" "+*" "*-" "*+" +/ -/ "/*" "*/" /+ /- "**" "//" =]] in \n $lexpression"
	   }
       } elseif {[nextSeparateur $chaine [list ++ --]]<0} {  # si c'est pas egal c'est ++ ou --
	   set erreur "Error in $chaine"
       }
	   
    }

 return $erreur
    
}
proc verifSyntaxeUpdate {chaine} {

    set listeSeparateur  [list ";" "if" "else"]
    set erreur ""
   set sep [nextSeparateur $chaine $listeSeparateur]
    while {($sep >-1)&&($erreur=="")} {

	if {([nextSeparateur $chaine [list "if" "else"]]==$sep)} {
	    if {([nextSeparateur $chaine [list "if"]]==$sep)} {
		set chaine [supNextExpression [gotonext $chaine] "if"]
		# Verifier la condition du if
		set erreur "[verifSyntaxeGarde [entreParenthesesGeneral $chaine] ]"
		if {($erreur!="")} {
		    set erreur "in if condition $erreur"
		} else {
		    set fermePar [indexFinTerme [supNextCar $chaine]]
		    set chaine [gotonext [string range $chaine [expr $fermePar+2] [string length $chaine] ]]
		}
	    } else {		
		set chaine [supNextExpression [gotonext $chaine] "else"]
	    }
	    if {($erreur=="")} { 
		set  fermeAccol  "[indexFermetureAccolade [supNextCar $chaine]]"
		# Verifier le code du if
		set  erreur "[verifSyntaxeUpdate [entreAccolade $chaine]]"
		set chaine "[gotonext [string range $chaine [expr $fermeAccol+2] [string length $chaine]  ] ]"
	    } 
	} else {
	    set contrainteGauche [nextExpression $chaine ";"]
	    set chaine [supNextExpression $chaine ";"]
#	    puts "procedure"
#	    set erreur [verifSyntaxeUpdateAtomique $contrainteGauche]
     	}

	set chaine [gotonext $chaine]
	set sep [nextSeparateur $chaine $listeSeparateur]

    }      

    
    if {($erreur=="")&&([gotonext $chaine] != "")} {
	set erreur "Missing \";\" in $chaine"
    }
#    if {$erreur==""} {
#	set erreur [verifSyntaxeUpdateAtomique $chaine]
#    }
    return $erreur
} 
