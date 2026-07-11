" Vim syntax file
" Language: Romeo CTS
" Maintainer: Didier Lime
" Latest Revision: April 27, 2020

if exists("b:current_syntax")
    finish
endif

" Keywords
syn keyword ctsDeclaration transition initially parameters skipwhite
syn keyword ctsCommand check simulate retime graph mincost with skipwhite
syn keyword ctsKeyword else if when for while do skipwhite
syn keyword ctsKeyword and or not skipwhite
syn keyword ctsKeyword return break continue skipwhite
syn keyword ctsKeyword cost intermediate speed priority allow cost_rate skipwhite
syn keyword ctsKeyword bounded deadlock  skipwhite
syn keyword ctsCommand minc minv maxc maxv skipwhite
syn keyword ctsNumber true false  skipwhite

" Types
syn keyword ctsType int byte double struct void const typedef enum skipwhite
syn keyword ctsType uint8_t uint16_t uint32_t uint64_t
syn keyword ctsType int8_t int16_t int32_t int64_t
syn keyword ctsType u8 u16 u32 u64
syn keyword ctsType i8 i16 i32 i64

" Identifier
syn match ctsIdentifier '[a-zA-Z\'_][a-zA-Z0-0\'_]*' skipwhite

" Integer
syn match ctsNumber '\<\d\+'
syn match ctsNumber '[+-]\d\+'
syn match ctsNumber '0x\x\+'
syn match ctsNumber '0b[01]\+'
syn keyword ctsNumber inf

" Float
syn match ctsNumber '\<\d\+\.\d*'
syn match ctsNumber '[+-]\d\+\.\d*'

" Comments
syn match ctsComment "//.*$"
syn region ctsComment start="/*" end="*/" fold transparent contains=ALL

" Blocks
syn region ctsBlock start='{' end='}' fold transparent contains=ALLBUT,transition,parameters,initially

let b:current_syntax = "cts"

hi def link ctsType Type
hi def link ctsNumber Constant
hi def link ctsKeyword Statement
hi def link ctsDeclaration PreProc
hi def link ctsCommand PreProc
hi def link ctsBlock Statement
hi def link ctsComment Comment
" hi def link ctsIdentifier Identifier

