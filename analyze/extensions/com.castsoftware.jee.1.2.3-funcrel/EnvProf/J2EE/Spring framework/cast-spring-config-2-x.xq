(: This is the default content for new XQuery Project files :)
declare namespace spring = "http://www.springframework.org/schema/beans"; (: not used in this file :)
declare namespace util   = "http://www.springframework.org/schema/util";
declare namespace jee    = "http://www.springframework.org/schema/jee";
declare namespace lang   = "http://www.springframework.org/schema/lang";
declare namespace tx     = "http://www.springframework.org/schema/tx";
import module namespace castbasics = "http://www.castsoftware.com/castbasics" at "../XQueryLibrary/CAST_BasicFunctions.xq";

declare variable $defaultAutowire as xs:string :=
       if (/*:beans/@default-autowire) 
       then string(/*:beans/@default-autowire)  
       else ""
;

declare variable $defaultDependencyCheck as xs:string :=
       if (/*:beans/@default-dependency-check)
       then string(/*:beans/@default-dependency-check)
       else ""
;

declare variable $defaultLazyInit as xs:string :=
       if (/*:beans/@default-lazy-init) 
       then string(/*:beans/@default-lazy-init)
       else ""
;


declare function local:createSpringBean(
      $bean as element())
      as xs:string   {
             let $beanName := (local:getBeanName($bean))
             let $beanClassName := if ( $bean/@class ) then $bean/@class else ""
             let $abstract := if ( $bean/@abstract ) then $bean/@abstract else ""
			 let $parent := if ( $bean/@parent ) then $bean/@parent else ""
			 let $factoryMethod := if ( $bean/@factory-method ) then $bean/@factory-method else ""
			 let $scope := local:getScopeAttribute( $bean )
			 let $autowire := local:getAutoWireAttribute($bean)
			 let $dependency-check := local:getDependencyCheckAttribute($bean) 
			 let $lazy-init := local:getLazyInitAttribute($bean)               
             let $createUtilConstantBean := for $utilBean in $bean/*:property/util:constant
                                               return local:createUtilConstantBean( $utilBean )
         return concat('createSpringBean("', 
                       string-join( ( $beanName, $beanClassName, $scope, $abstract, $parent, $autowire, $dependency-check, $lazy-init, $factoryMethod ), '", "' ), 
                       '" );',
                       castbasics:CR(),
                       $createUtilConstantBean )
 };
 

declare function local:getBeanName($bean as element()) as xs:string
{
       if ($bean/@id)
       then $bean/@id
       else if ($bean/@name)
       			then $bean/@name
       			else if ($bean/@class)
       			     then $bean/@class
       			     else $bean/@transaction-manager
};

declare function local:getScopeAttribute( $bean as element() ) as xs:string
{
      if ( $bean/@scope )
      then $bean/@scope
      else "singleton"
};

declare function local:getAutoWireAttribute( $bean as element() ) as xs:string
{
       if ( $bean/@autowire )
       then if ( $bean/@autowire != 'default' )
            then $bean/@autowire
            else $defaultAutowire
       else ""
};

declare function local:getDependencyCheckAttribute($bean as element()) as xs:string
{
       if ( $bean/@dependency-check )
       then if ( $bean/@dependency-check != 'default' )
            then $bean/@dependency-check
            else $defaultDependencyCheck
       else ""
};

declare function local:getLazyInitAttribute($bean as element()) as xs:string
{
       if ( $bean/@lazy-init )
       then if ( $bean/@lazy-init != 'default' )
            then $bean/@lazy-init
            else $defaultLazyInit
       else ""
};

declare function local:getUtilConstantName( $bean as element() ) as xs:string
{
      if ( $bean/@id )
      then $bean/@id
      else $bean/@static-field
};

declare function local:createUtilConstantBean( $bean as element() ) as xs:string
{
      let $beanName := local:getUtilConstantName( $bean )
      let $scope := local:getScopeAttribute( $bean )
      return concat( 'createSpringBean("', 
                     string-join( ( $beanName, 'org.springframe_work.beans.factory.config.FieldRetrievingFactoryBean', $scope ), '", "' ),  
                     '" );',
                     castbasics:CR() )
};

declare function local:createUtilPropertyPath( $bean as element() ) as xs:string
{
      let $scope := local:getScopeAttribute( $bean )
      return concat( 'createSpringBean("', 
                     string-join( ( $bean/@id, 'org.springframework.beans.factory.config.PropertyPathFactoryBean', $scope ), '", "' ),  
                     '" );',
                     castbasics:CR() )
};

declare function local:createUtilCollectionBean( $bean as element(), $class as xs:string ) as xs:string
{
      let $scope := local:getScopeAttribute( $bean )
      return concat( 'createSpringBean("', 
                     string-join( ( $bean/@id, $class, $scope ), '", "' ),  
                     '" );',
                     castbasics:CR() )
};

declare function local:getUtilListClass( $bean as element() ) as xs:string
{
      if ( $bean/@list-class )
      then $bean/@list-class
      else "java.util.List"
};

declare function local:getUtilSetClass( $bean as element() ) as xs:string
{
      if ( $bean/@set-class )
      then $bean/@set-class
      else "java.util.Set"
};

declare function local:getUtilMapClass( $bean as element() ) as xs:string
{
      if ( $bean/@map-class )
      then $bean/@map-class
      else "java.util.Map"
};


declare function local:createJndiLookup( $bean as element() ) as xs:string
{
      concat( 'createSpringBean("', 
              string-join( ( $bean/@id, 'org.springframework.jndi.JndiObjectFactoryBean', 'singleton' ), '", "' ),  
              '" );',
              castbasics:CR() )
};


declare function local:createLocalSlsb( $bean as element() ) as xs:string
{
      concat( 'createSpringBean("', 
              string-join( ( $bean/@id, 'org.springframework.ejb.access.LocalStatelessSessionProxyFactoryBean', 'singleton' ), '", "' ),  
              '" );',
              castbasics:CR() )
};


declare function local:createRemoteSlsb( $bean as element() ) as xs:string
{
      concat( 'createSpringBean("', 
              string-join( ( $bean/@id, 'org.springframework.ejb.access.SimpleRemoteStatelessSessionProxyFactoryBean', 'singleton' ), '", "' ),  
              '" );',
              castbasics:CR() )
};


declare function local:addBeanAlias( $alias as element() ) as xs:string
{
      concat( 'addAlias("',
              string-join( ( $alias/@name, $alias/@alias ), '", "' ),
              '" );',
              castbasics:CR() )
};


declare function local:createJstlLinks( $bean as element() ) as xs:string
{
      for $property in $bean/*:property
      where $property/@name = "url"
      return concat( 'createJstlLink( "',
                     string-join( ( local:getBeanName( $bean ), $property/*:value | $property/@value ), '", "' ),
                     '" );',
                     castbasics:CR() )
      
};



declare function local:createXmlViewLinks( $bean as element() ) as xs:string
{
      for $property in $bean/*:property
      where $property/@name = "location"
      return concat( 'createXmlViewLink( "',
                     string-join( ( local:getBeanName( $bean ), $property/*:value | $property/@value ), '", "' ),
                     '" );',
                     castbasics:CR() )
};


declare function local:createSqlQueryLinks( $bean as element() ) as xs:string
{
      (: 
	   : We use normalize-space to remove all line breaks, otherwise CAST script engine fails
	   : Drawback: it also replaces all internal sequences of white space with one, even in SQL strings
	   : E.g SELECT to_date( :dateEffet, 'YYYY    MMDD' ) dateeffet FROM table will become 
	   :     SELECT to_date( :dateEffet, 'YYYY MMDD' ) dateeffet FROM table
	   :)
      for $property in $bean/*:property
      where $property[contains(@name,"sql")]
      return concat( 'createSqlQueryLink( "',
                     string-join( ( local:getBeanName( $bean ), replace(fn:normalize-space($property/*:value | $property/@value), '"', '\\"') ), '", "' ),
                     '" );',
                     castbasics:CR() )
};


declare function local:linkXMLFiles( $importedFile as element() ) as xs:string
{
      let $path := $importedFile/@resource
      return concat( 'createLinkToIncludedFile( "',
                     $path ,
                     '" );',
                     castbasics:CR() )
};




(: declaration of the global variables :)
concat("use Core.JEE.Spring.Spring;", castbasics:CR()),
concat("use Core.JEE.JEE;", castbasics:CR()),
concat("use Core.Log;", castbasics:CR()),
concat("use Core.Error;", castbasics:CR()),
concat("use Core.ConstantsMetamodel;", castbasics:CR(), castbasics:CR(), castbasics:CR()),



(: Objects Creation :)



(: creation of Spring beans :)
for $bean in /*:beans/*:bean
return local:createSpringBean($bean),



(: util schema :)

(: creation of Spring beans for tag util:constant :)
for $utilConstant in /*:beans/util:constant
return local:createUtilConstantBean($utilConstant),

(: creation of Spring beans for tag util:property-path :)
for $utilPropertyPath in /*:beans/util:property-path
return local:createUtilPropertyPath($utilPropertyPath),

(: creation of Spring beans for tag util:list :)
for $utilList in /*:beans/util:list
return local:createUtilCollectionBean( $utilList, local:getUtilListClass( $utilList ) ),

(: creation of Spring beans for tag util:set :)
for $utilSet in /*:beans/util:set
return local:createUtilCollectionBean( $utilSet, local:getUtilSetClass( $utilSet ) ),

(: creation of Spring beans for tag util:map :)
for $utilMap in /*:beans/util:map
return local:createUtilCollectionBean( $utilMap, local:getUtilMapClass( $utilMap ) ),




(: jee schema :)
(: creation of Spring beans for tag jee:jndi-lookup :)
for $jeeJndiLookup in /*:beans/jee:jndi-lookup
return local:createJndiLookup( $jeeJndiLookup ),

(: creation of Spring beans for tag jee:local-slsb :)
for $jeeLocalSlsb in /*:beans/jee:local-slsb
return local:createLocalSlsb( $jeeLocalSlsb ),

(: creation of Spring beans for tag jee:remote-slsb :)
for $jeeRemoteSlsb in /*:beans/jee:remote-slsb
return local:createRemoteSlsb( $jeeRemoteSlsb ),




(: lang schema :)
(: creation of Spring beans for lang namespace :)
for $langBean in /*:beans/lang:*
return local:createSpringBean( $langBean ),


(: tx schema :)
(: creation of Spring beans for tx namespace :)
for $txBean in /*:beans/tx:*[(@name and string-length(@name)!=0) or (@class and string-length(@class)!=0) or (@transaction-manager and string-length(@transaction-manager)!=0) or (@id and string-length(@id)!=0)]
return local:createSpringBean( $txBean ),


(: bean aliases :)
for $alias in /*:beans/*:alias
return local:addBeanAlias( $alias ),




(: Links Creation :)
concat( castbasics:CR(), castbasics:CR(), castbasics:CR() ),



(: links with Jstl Views :)
for $jstlBean in /*:beans/*:bean
where $jstlBean/@class = "org.springframework.web.servlet.view.JstlView"
return local:createJstlLinks( $jstlBean ),


(: links with XML Views Resolver :)
for $xmlView in /*:beans/*:bean
where $xmlView/@class = "org.springframework.web.servlet.view.XmlViewResolver"
return local:createXmlViewLinks( $xmlView ),

for $importedFile in /*:beans/*:import
return local:linkXMLFiles($importedFile), 


(: links with SQL query :)
for $bean in /*:beans/*:bean
where not(empty($bean/*:property[contains(@name,"sql")]))
return local:createSqlQueryLinks($bean)

