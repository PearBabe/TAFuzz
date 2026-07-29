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

#package require Img
global basePath
wm title  . "About Romeo"

image create photo logoRomeo -file "$basePath/img/romeo.png"

# frame sup�rieur
label .logo -image logoRomeo
pack .logo -side top

label .title -text "Romeo" 
font create title_font -size 20 -weight bold
.title configure -font title_font
pack .title -side top

label .version -text "v2.9.1"
font create version_font -size 10
.version configure -font version_font
pack .version -side top

font create licence_font -size 10 -slant italic
label .licence -text "Released under the CeCILL Licence" -font licence_font
pack .licence -side top

label .contact_title -text "Contact:" -font [font create -size 12 -weight bold]
label .contact_mail -text "romeo@irccyn.ec-nantes.fr" -font [font create -size 12]
pack .contact_title -side top
pack .contact_mail -side top
