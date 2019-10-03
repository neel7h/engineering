In progress
-----------


Done
----

- metric CodeLinesCount is calculated by us because UA calculation is too slower

- Deactivate Avoid Artifacts with high Commented-out Code Lines/Code Lines ratio
	**** should find another solution than language pattern, which is slower
	
- set line of code to zero for files uaxdirectory/sqltablesize 
- remove inheritance to APM Sources for sql objects

- remove 'one path' of inheritance to APM Sources for sql objects

- remove empty lines from objects LOC

- Added MA v2 definition in SQLSCriptCastMetrics for 1523 sub-type, QR Avoid using SQL queries inside a loop
	
- Added comment for CodeLinesCount metric
- Deactivated : Avoid Artifacts with high Commented-out Code Lines/Code Lines ratio

- Deactivated : Avoid SQL queries using functions on indexed columns in the WHERE clause : 
  - activated and has always 4 grade...
  - why is it activated ? non empty total ? or because we have other database tech in teh same KB ?
    - total is DIAG_ALL_ANA_SQL_ARTI_TOTAL ==> so count all our objects
  ==> I cannot repair this!
  ==> I can push violations for it...
 
- whitespaces from the end of an object name, for the cases when in the sql file we have "A " and A which are the same in DB2 have been stripped, you'll see rstrip(' ') when variant is db2, and what it remains is to do the same for the rest of variants; so fixed for db2 udb :
	create schema "toto" -- ok
	create schema "toto " -- cannot create
	create schema " toto " -- ok
	create schema " toto" -- cannot create

- fix Avoid Artifacts with SQL statement including subqueries
-- when it doesn't work for some MS SQL test case

- Fixed Avoid Artifacts with High Depth of Nested Subqueries  : 
        CAST_SQL_Metric_MaxNestedSubqueriesDepth.maxDepth is moved with CopyMaxDepth to CAST_MetricAssistant_Metric_maxSQLSubqueriesNestedLevels.maxSQLSubqueriesNestedLevels
        
- altering a renamed table produced an error in the log

- corrected multi-line splitted identifier for DB2 : 
      CONSTRAINT VA_VIEW_ID PRIMARY KEY (VA_VIEW_ID,VA_AT_ID,VA_BO_NUMBE
R))

- Corrects 7346 Avoid redundant indexes
  - add CAST_WithOrder.order on index --relyon--> colmun through app level
  - add inheritance on index CAST_AST_ANSISQL_Indexable

- install script simplification : speeds up manage extension

- columns should not inherit from APM SQLScript Artifacts ? as they appear in total count...
 ==>  major grade change due to modification of rule's total 
total is diminueshed so grade is lower for following rules :
  - 7344  Avoid "SELECT *" queries
  - 7808  Avoid Artifacts with SQL statement including subqueries

- ua analysis options and file extension overrides

- unicode identifiers

- change also current schema name during 2nd pass of parsing (so that we get the same objects)
- corrects a bug in parse_identifier : full rewrite
- bad column name in sql server case : [column_name] [varchar]
- USE [...] is not a schema change in sql server
- one error in coeexample postgresql due to keyword..


- XXL :
  - read tablesize as input and generate violations
  - adapt 'total' so that do not have  

Todo
----
- Informix : ":" est le separateur entre database et objets
	Voici quelques examples/liens
	
	Access other database servers : http://www.ibm.com/support/knowledgecenter/SSGU8G_11.70.0/com.ibm.sqlt.doc/ids_sqt_287.htm
	When the external database is on the same database server as the current database, you must qualify the object name with the database name and a colon. 
	For example, to refer to a table in a database other than the local database, the following SELECT statement accesses information from an external database:
		SELECT name, number FROM salesdb:contacts
		In this example, the query returns data from the table, contacts, that is in the database, salesdb.
	
	http://www.ibm.com/support/knowledgecenter/SSGU8G_11.70.0/com.ibm.ddi.doc/ids_ddi_222.htm#ids_ddi_222
	Typically, you use a synonym to refer to tables that are not in the current database. 
	For example, you might execute the following statements to create synonyms for the customer and orders table names:
		CREATE SYNONYM mcust FOR masterdb@central:customer;
		CREATE SYNONYM bords FOR sales@boston:orders;

	To those users, the customer table is external. 
	Does this mean you must prepare special versions of the programs and reports, versions in which the customer table is qualified with a database server name?
	A better solution is to create a synonym in the users' database, as the following example shows:
		DATABASE stores_demo@nantes;
		CREATE SYNONYM customer FOR stores_demo@avignon:customer;
		
	Create joins between external database servers : http://www.ibm.com/support/knowledgecenter/SSGU8G_11.70.0/com.ibm.sqlt.doc/ids_sqt_289.htm
	When you specify the database name explicitly, the long table names can become cumbersome unless you use aliases to shorten them, as the following example shows:
	SELECT O.order_num, C.fname, C.lname
	   FROM masterdb@central:customer C, sales@boston:orders O
	   WHERE C.customer_num = O.Customer_num

- unicode identifiers : ...

- store detected variant on objects ?

- remove all keywords of lexer except basic ones
	after a quick test, if we remove all keywords we have 10 failures, 1 error form 55 integration tests (we have a total of 58 but 3 are skipped)

- test client server...
  - the fact that table names are not UPPER CASE may miss client server links, due to average design choice of C/S module

- whitespaces from the end of an object name, for the cases when in the sql file we have "A " and A which are the same in DB2 have been stripped, you'll see rstrip(' ') when variant is db2 has been fixed, and what it remains is to do the same for the rest of variants. MS SQL, Sybase and DB2 seems to have the same pattern & behavior, should be confirmed. PostgreSQL it takes in account all spaces, no matter where we add them so there is nothing to do for that one.  It remains to see what could be done for Oracle and MariaDB.
Here's is how each various rdbms deal with whitespaces :
-- MS SQL
	create database "toto" -- ok
	create database "toto " -- cannot create
	create database " toto " -- ok
	create database " toto" -- cannot create

-- Sybase
	create database "toto" -- ok
	create database "toto " -- cannot create
	create database " toto " -- ok
	create database " toto" -- cannot create
	
-- MariaDB
	create database `castpubs`-- ok
	create database `	castpubs`-- ok
	create database `	castpubs  ` -- incorrect
	create database `castpubs  `-- incorrect
	
-- db2 udb, this one is fixed
	create schema "toto" -- ok
	create schema "toto " -- cannot create
	create schema " toto " -- ok
	create schema " toto" -- cannot create
	
-- oracle
	CREATE USER "toto"  -- ok
		IDENTIFIED BY toto 
		DEFAULT TABLESPACE example 
		TEMPORARY TABLESPACE temp
		QUOTA unlimited ON example 

	CREATE USER "toto " -- ok
		IDENTIFIED BY toto 
		DEFAULT TABLESPACE example 
		TEMPORARY TABLESPACE temp
		QUOTA unlimited ON example 

	CREATE USER " toto " -- ok
		IDENTIFIED BY toto 
		DEFAULT TABLESPACE example 
		TEMPORARY TABLESPACE temp
		QUOTA unlimited ON example 


	CREATE USER " toto" -- ok
		IDENTIFIED BY toto 
		DEFAULT TABLESPACE example 
		TEMPORARY TABLESPACE temp
		QUOTA unlimited ON example 
		
-- postgresql
	create schema "toto" -- ok
	create schema "toto " -- ok
	create schema " toto " -- ok
	create schema " toto" -- ok
	

Old Todo:
---------

false positive 

cartesian product 

select count(*)  into L_exists
from salesdetail as deteled, salesdetail where salesdetail.title_id = deteled.title_id;

select * 
-- create temporary table t_sales as Select * From sales;


Parsing issue on :

    ALTER TABLE ONLY wk_dia_jeepath ALTER COLUMN id SET DEFAULT nextval('wk_dia_jeepath_id_seq'::regclass);



issues : 

- put indexes and foreign key under their respective tables ?
  argument is that both are equivalent, so it is possible to have same semantics with table constraint inline and alter... 
  
- sybase create proc with statement list not correctly parsed

- 1608  Avoid cascading Triggers
  - no table --fire--> trigger so no rule 


- NBI says : avoid queries with more than 4 tables do not work at all (MAv2...)
- NBI says 
  - that function call on indexed columns is interesting (not the same remediation as no index)
  - no index can support remediation is add index
  - better have false positives (he is in pilot mode)
 


- incorrect type for attrnam (should be character varying(255)): 
CREATE TABLE anaattr (
    session_id integer NOT NULL,
    attrnam character varying(255) NOT NULL,
    intval integer
)
WITH (autovacuum_enabled=off);

- index on views
- with clause

- view columns are not created (but no one complained)


- do not have 'plugin' name in xml2dbscope as it is local... 
- doc : 
  - first step : relocate ids 
- do we need at least 2 xxl table in the cartesian product ? no
        
        
Rules
-----


In progress
-----------


MAv2
----

- remove MAv2 as it is not reliable
-- see SQLScriptCastMetrics : Use of select All for a case not detected by UA; Cyclomatic Complexity seems to not be covered by UA



Feasible ?
----------

TRUE    9   7642    Avoid SQL queries on XXL tables not using the first column of a composite index in the WHERE clause
FALSE   6   7428    Avoid SQL queries not using the first column of a composite index in the WHERE clause
--> débile ?
--> 'not used by js'

TRUE    9   7658    Avoid SQL queries on XXL Tables using Functions on indexed Columns in the WHERE clause
--> activated because presence of XXL tables and all technos

FALSE   9   7418    Avoid SQL queries using functions on indexed columns in the WHERE clause
--> useless : 'explanation' of no index can support
--> 'not used by js'

SQL ?
-----

- should we support notation "db1.scheme1.table1", "db1..table1" by the parser?

- How should we support case-sensitivity for table/column names?
 
  (1)	to assume the scripts use the same case when referring to the same table/column (bias towards case-sensitive)
  (2)	to assume table/column names are different (different letters) and thus consider case insensitive everything (bias towards case-insensitive)
 
  Currently case-INsensitive equalities are implemented for DROP and RENAME (2). 


SQL With parameter
------------------


Hard or very hard ?
-------------------

FALSE   8   1588    Use WHEN OTHERS in exception management
- https://jira.castsoftware.com/browse/DIAG-449
- PL/SQL
EXCEPTION
     WHEN DUP_VAL_ON_INDEX THEN
        raise_application_error (-20001,'You have tried to insert a duplicate value.');

    WHEN OTHERS THEN
        raise_application_error(-20001,'An error was encountered - '||SQLCODE||' -ERROR- '||SQLERRM);

END; 

- postgresql 
BEGIN

EXCEPTION ...

EXCEPTION WHEN OTHERS
 
END

- mysql 

DECLARE action HANDLER FOR condition_value statement;

- db2 

DECLARE ... HANDLER FOR ...

DECLARE ... HANDLER FOR SQLEXCEPTION
@see https://www.toadworld.com/platforms/ibmdb2/w/wiki/6701.declare-handlers

- sql server : no best practice ?
 
--> I can do in cases I find (postgresql, ...)


FALSE   9   7420    Avoid SQL queries with implicit conversions in the WHERE clause
TRUE    9   7662    Avoid SQL queries on XXL Tables with implicit conversions in the WHERE clause


Probably already working ?
--------------------------

TRUE    7   7424    Avoid using SQL queries inside a loop --> client server
FALSE   9   7510    Use only Hibernate API to access to the database
TRUE    9   7742    Avoid SQL injection vulnerabilities ( CWE-89 )



Other candidates
----------------

- Avoid cascading Triggers  https://jira.castsoftware.com/browse/DIAG-2121
- Avoid nested Triggers https://jira.castsoftware.com/browse/DIAG-779
- Avoid recursive Triggers https://jira.castsoftware.com/browse/DIAG-809

Ideas of new rules
------------------
 
- Avoid useless indexes : if an index is never use... 
  - do not resist to missing client server analysis
  - but valuable : GDI says the plague is that there are too many indexes
  
- joins should follow foreign keys
  - GDI says : FN2 or FN3 
- suggested indexes : queries are using such and such columns for such table...
  - GDI says 'low value because the tool already exists in sqlserver, oracle and probably others
- index non discriminant : example index on enum


TODO
====

- do 'function' may be accepted as function name ?
    select * from table1, table2 where function(table1.col) = function(table2.col);
    --> generates false violations...
    
- partially resolve override by looking at param number ?

- false recursive call for : 
create procedure toto()
begin

  select * from toto where a in (select * from titi) ;

end;


- http://www.postgresql.org/docs/7.3/static/xfunc-tablefunctions.html


Objects
-------

- pg : 
CREATE TABLE orders (
    order_id integer PRIMARY KEY,
    product_no integer REFERENCES products (product_no),
    quantity integer
);

- ALTER TABLE "CASTPUBS"."AUTHORS" MODIFY ("AU_FNAME" NOT NULL ENABLE);
- skipp autogenerated comments by extractors 
- create table inside procedure
- create local temporary table (postgres)
- parse inside strings too : may contain create table
- COMMENT ON ...


Object Structure
++++++++++++++++

- SQLServer 
  - Existing Analyser :  Instance -> Database -> Schema -> Table
  - DDL extracted though SQL Admin Studio :
  
    USE <database name>
    ...
    CREATE TABLE [<schema name>].[<table name>] ...

- Oracle
  - Existing Analyser :  Instance -> Schema -> Table
  - DDL extracted with Oracle SQL Developer :
    
    CREATE TABLE "<schema name>"."<table name>" ...


Links
-----

Quality Rules
-------------

- todo


Potential 

- Avoid queries using old style join convention  instead of ANSI-Standard joins


Samples
=======

MySQL
-----

  https://github.com/LittleZ/mySQL-samples
  https://github.com/wholraj/tuto-iOS-ws-php-mysql/blob/master/db/db.sql
  https://github.com/huhushow/mysql-script/blob/master/random.sql
  https://github.com/marlenunez/simple-blog/blob/master/blog.sql



Humm
====

- C'est quoi ce bordel ? : 
  - V:\MASS\DEXIA_BANK Des fichiers de 22 megs quasi vides ?

- db2 udb : V:\MASS\DexiaBank\lang\sqlpsm 
  - je ne comprends pas la structure (CONNECT TO ...) est ce un genre de schema ?


Squirrel Extractor generates zounds of 1k files
-----------------------------------------------

Maybe that is why it lags ?
Compare on same code...

Oracle Not really needed ?
--------------------------

- oracle APPS : V:\MASS\APPS\DB-SCRIPT 
  - one source file of 1.5G...
  - where does it come from ? 

- ask for mass tests oracle 
  - OraApps:  \\productfs01\SrvSourcesDev\EngDEV\SQUIRREL\Contrex\Oracle\HugeTestsSources\OraAPPS
  - see : \\productfs01\SrvSourcesDev\EngDEV\SQUIRREL\mass
    - use parser to split this file into :
      - one file per package body/header
      - one file for the rest tables, trigger, etc...
  
Thoughts
========
  
- need smarter XML2DB scope to allow add techno to existing QR
- 'all techno' rules seem to work out of the box for a new language when detail/total proc are 'well written' : all objects inherit from Cat
  - TechnoSQL rules seem to be well written
  - but impl is badly documented : no explanation of what is the input contract (object inheritance, links etc...)  

- property/scope difficulty on some rules seem to be a good sample ?

- unified :
 
  - working : 7820  Never use SQL queries with a cartesian product
      DIA_MANY_AVOIDCARTESIAN : handles multi techno and bookmark/no bookmark
      DIT_MANY_SQLARTFUSETAB : exist link to table ?
      
  - not working : 7424  Avoid using SQL queries inside a loop

 
Ideas
=====
 
    

 
 