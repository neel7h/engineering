(: This is the default content for new XQuery Project files :)
declare namespace ejb3 = "http://java.sun.com/xml/ns/javaee";
import module namespace castbasics = "http://www.castsoftware.com/castbasics" at "../XQueryLibrary/CAST_BasicFunctions.xq";

declare function local:createEJBSession(
      $ejb as element(),
      $sessionType as xs:string)
      as xs:string
      {         
         let $ejbName := $ejb/*:ejb-name
         let $ejbClassName := $ejb/*:ejb-class       
         let $ejbLocalInterfaceName := $ejb/*:local
         let $ejbRemoteInterfaceName := $ejb/*:remote     
         
         return concat("createEJBSession (""",
                             normalize-space($ejbName), """,""",
                             normalize-space($ejbClassName),  """,""",
                             normalize-space($ejbLocalInterfaceName),  """,""",
                             normalize-space($ejbRemoteInterfaceName),   """,""",
                             $sessionType,  """,",  "false);", 
                             castbasics:CR())
      };

declare function local:createEJBMDB(
      $ejb as element())
      as xs:string
      {
         let $ejbName := $ejb/*:ejb-name
         let $ejbClassName := $ejb/*:ejb-class
        
         return concat("createEJBMDB (""",$ejbName, """,""",normalize-space($ejbClassName),""");", castbasics:CR()) 
      };
      
declare function local:setEjbRemovePropertyOnMethod(
      $ejb as element(),      $ejbRemoveMethodNames as xs:string
      )
      as xs:string
      {	  
         let $ejbName := $ejb/*:ejb-name      
         let $ejbClassName := $ejb/*:ejb-class       
         return concat("setEjbRemovePropertyOnMethod (""",$ejbName, """,""",
                                         normalize-space($ejbClassName),  """,""",
                                         $ejbRemoveMethodNames,""");", castbasics:CR()) 
      };

declare function local:setEjbMethodIsSecuredPropertyOnMethod( $methodPermission as element() )
      as xs:string
      {
		 let $methodName := $methodPermission/*:method-name
         let $ejbName := $methodPermission/*:ejb-name
		 let $ejbRemoteInterfaceName :=	/*:ejb-jar/*:enterprise-beans/*:session[contains(*:ejb-name, $ejbName)]/*:remote		 
         return concat("setEjbMethodIsSecuredPropertyOnMethod (""",$ejbName, """,""",
                                         $ejbRemoteInterfaceName,  """,""",
                                         $methodName,  """,""",
                                         $ejbName,""");", castbasics:CR()) 										 
      };

(: declaration of global variables :)
concat("use Core.JEE.JEE;", castbasics:CR()),
concat("use Core.Log;", castbasics:CR()),
concat("use Core.Error;", castbasics:CR()),
concat("use Core.ConstantsMetamodel;", castbasics:CR()),
concat("use Core.JEE.EJB.EJB3;", castbasics:CR()),

(: creation of stateless EJB :)
for $stateless in /*:ejb-jar/*:enterprise-beans/*:session[contains(*:session-type, 'Stateless')]
return local:createEJBSession($stateless,"Stateless"),
(: creation of stateful EJB :)
for $stateful in /*:ejb-jar/*:enterprise-beans/*:session[contains(*:session-type, 'Stateful')]
return local:createEJBSession($stateful,"Stateful"),
(: tag remove methods of the stateful EJB :)
for $stateful in /*:ejb-jar/*:enterprise-beans/*:session[contains(*:session-type, 'Stateful')]
for $ejbRemoveMethodNames in /*:ejb-jar/*:enterprise-beans/*:session/*:remove-method/*:bean-method/*:method-name
return local:setEjbRemovePropertyOnMethod($stateful,$ejbRemoveMethodNames),
for $methodPermission in /*:ejb-jar/*:assembly-descriptor/*:method-permission/*:method
	return local:setEjbMethodIsSecuredPropertyOnMethod($methodPermission),
(: creation of message driven bean EJB :)
for $mdb in /*:ejb-jar/*:enterprise-beans/*:message-driven
return local:createEJBMDB($mdb)
