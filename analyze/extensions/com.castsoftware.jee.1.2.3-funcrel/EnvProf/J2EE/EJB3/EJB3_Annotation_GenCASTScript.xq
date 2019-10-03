(: This is the default content for new XQuery Project files :)
import module namespace castbasics = "http://www.castsoftware.com/castbasics" at "../XQueryLibrary/CAST_BasicFunctions.xq";

declare function local:getEJBName($ejb as element()) as xs:string
{
       if ($ejb/anno/mem[contains(name,'name')])
       then castbasics:substring-after-last($ejb/anno/mem[contains(name,'name')]/../val, ".")
       else castbasics:substring-after-last($ejb/../name, ".")
};
	  
declare function local:createEJBSession(
      $ejb as element(),
      $sessionType as xs:string)
      as xs:string   {
         let $ejbName := local:getEJBName($ejb)
         let $ejbClassName := $ejb/../name
         let $len := string-length($ejbClassName)
         let $ejbRemoteInterfaceName := $ejb/../anno[contains(name,'javax.ejb.Remote')]/mem[contains(name, 'value')]/val
         let $ejbLocalInterfaceName := $ejb/../anno[contains(name,'javax.ejb.Local')]/mem[contains(name, 'value')]/val
         
         return concat("createEJBSession (""",
                                  $ejbName, """,""",
                                  $ejbClassName,  """,""",
                                  $ejbLocalInterfaceName,  """,""",
                                  $ejbRemoteInterfaceName,   """,""",
                                  $sessionType,  """,",  "true);",
                                  castbasics:CR())
 };

declare function local:createEJBMDB(
      $ejb as element())
      as xs:string
      {       
         let $ejbName := local:getEJBName($ejb)
         let $ejbClassName := $ejb/../name
        
         return concat("createEJBMDB (""",$ejbName, """,""",$ejbClassName,""");", castbasics:CR()) 
      };

(: declaration of the global variables :)
concat("use Core.JEE.JEE;", castbasics:CR()),
concat("use Core.Log;", castbasics:CR()),
concat("use Core.Error;", castbasics:CR()),
concat("use Core.ConstantsMetamodel;", castbasics:CR()),
concat("use Core.JEE.EJB.EJB3;", castbasics:CR()),

(: creation of stateless EJB :)
for $stateless in /decls/decl/anno[contains(name,'javax.ejb.Stateless')]
return local:createEJBSession($stateless,"Stateless"),

(: creation of stateful EJB :)
for $stateful in /decls/decl/anno[contains(name,'javax.ejb.Stateful')]
return local:createEJBSession($stateful,"Stateful"),

(: creation of message driven bean EJB :)
for $mdb in /decls/decl/anno[contains(name,'javax.ejb.MessageDriven')]
return local:createEJBMDB($mdb)
