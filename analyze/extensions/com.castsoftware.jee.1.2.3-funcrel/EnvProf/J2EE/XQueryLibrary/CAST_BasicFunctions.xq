(: This is the default content for new XQuery Project files :)

module namespace castbasics = "http://www.castsoftware.com/castbasics";

declare function castbasics:CR() as xs:string
{
      "&#10;"
};

declare function castbasics:substring-after-last(
     $string as xs:string?, 
     $delim as xs:string) 
     as xs:string?
{
      if (contains ($string, $delim))
      then castbasics:substring-after-last(substring-after($string, $delim), $delim)
      else $string
};

declare function castbasics:substring-before-if-contains 
  ( $arg as xs:string? ,
    $delim as xs:string )  as xs:string? {
       
   if (contains($arg,$delim))
   then substring-before($arg,$delim)
   else $arg
 } ;
 
declare function castbasics:debug(
      $message as xs:string)
      as xs:string
{
      concat ("log(DEBUG, """,$message,""");",castbasics:CR())
}; 

declare function castbasics:escape-string(
        $arg as xs:string? )
        as xs:string {
  replace($arg, '("|''|\\)', '\\$1')
}; 