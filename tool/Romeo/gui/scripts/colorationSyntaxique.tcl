global motsCles motsClesType motsClesChiffres motsClesOperateurs motsClesEnNoir
global fontSizeEditor

set fontSizeEditor 12

set motsCles {(\}|\{|\(|\)|\n|;| |\t|\r|\r\n|\n)+(for|while|if|else|do|return)(\{|\(|\n|\t|\r| )}

set motsClesType {(\}|\{|\[|\]|\(|\)|\n|;| |\t|\r|\r\n|\n)+(typedef|struct|const|double|int|uint8_t|int8_t|uint16_t|int16_t|uint32_t|int32_t|uint64_t|int64_t|char|void)(\{|\(|\n|\t|\r| |\[|\])}

set motsClesEnNoir {\(|\)|\{|\}|;|,|\[|\]}

set motsClesCommentaires {\/\/ .*\n|\/\* (.|\n)*\*\/}

set motsClesOperateurs {\+|\-|\*|\/|\=|&&|!|>|<|\|\|}

proc configureCouleur {fenetre} {
global  motsCles motsClesType motsClesCommentaires motsClesOperateurs motsClesEnNoir

    $fenetre tag config motCle -foreground blue
    $fenetre tag config motCleType -foreground forestgreen
    $fenetre tag config motCleOperateur -foreground purple
    $fenetre tag config motCleEnNoir -foreground black
    $fenetre tag config motCleCommentaire -foreground darkred

}




proc colorationSyntaxique {fenetre} {
global motsCles motsClesType motsClesCommentaires motsClesOperateurs motsClesEnNoir fontSizeEditor
global tpn

#pathName tag delete tagName ?tagName
#pathName configure ?option? ?value option value ...?
 modifTPN $tpn(courant)


    $fenetre tag delete motCle
    $fenetre tag delete motCleType
    $fenetre tag delete motCleCommentaire
    $fenetre tag delete motCleEnNoir
    $fenetre tag delete motCleOperateur

    configureCouleur $fenetre

  #  $fenetre tag configure -txt -foreground blue
    colorer $fenetre $motsCles motCle
    colorer $fenetre $motsClesType motCleType
    colorer $fenetre $motsClesOperateurs motCleOperateur
    colorer $fenetre $motsClesEnNoir motCleEnNoir
    colorer $fenetre $motsClesCommentaires motCleCommentaire


}


proc colorer {fenetre regExp tag {indiceDebut "1.0"} {indiceFin "end"}} {
set debut $indiceDebut
set listeIdsTags [list]

set indTrouveDebut "on cherche"
while {$indTrouveDebut != ""} {

set indTrouveDebut [$fenetre search -nocase -count longueur \
-regexp -nocase $regExp $debut $indiceFin]

if {$indTrouveDebut != ""} {
set indTrouveFin "$indTrouveDebut + $longueur char"
lappend listeIdsTags $indTrouveDebut $indTrouveFin
set debut $indTrouveFin


}
}

if {[llength $listeIdsTags] > 0} {
eval "$fenetre tag add $tag $listeIdsTags"
}
}

# Voici une manière de l'utiliser :
#text .txt
#pack .txt -side left -fill both
#..txt tag config motCle -foreground blue

#..txt insert end {
#global maVar
#set maVar $maValeur




