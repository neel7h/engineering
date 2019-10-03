Features
========

- Create table, view, column, index, foreign key, triggers, packages and procedure/function, events objects
- select/insert/update/delete links to tables/views
- call to procedures/functions
- call link to triggers when it is triggered by insert/update/delete
- DML analysis and link to a dependent analysis unit
- XXL and XXS quality rule support :
  - sqltablesize file in the same place as sources selected for analysis (put it near sources)
- Rules 
Quality rules :
1634	Avoid unreferenced Tables
7130	Avoid Artifacts with High Depth of Nested Subqueries
7344	Avoid "SELECT *" queries
7346	Avoid redundant indexes
7348	Avoid too many Indexes on one Table
7388	Avoid artifacts having recursive calls
7390	Avoid having multiple Artifacts inserting data on the same SQL Table
7394	Avoid having multiple Artifacts updating data on the same SQL Table
7392	Avoid having multiple artifacts deleting data on the same SQL table
7404    Avoid unreferenced views
7424	Avoid using SQL queries inside a loop
7436    Prefer UNION ALL to UNION
7762	Avoid undocumented triggers, functions and procedures
7776    Avoid Artifacts with High Fan-In
7778    Avoid Artifacts with High Fan-Out
7808	Avoid Artifacts with SQL statement including subqueries
7814	Avoid Tables not using referential integrity
7860	Avoid unreferenced Functions
1101000	Never use SQL queries with a cartesian product *
1101002	Never use SQL queries with a cartesian product on XXL Tables *
1101004	Avoid non-indexed SQL queries *) *
1101006	Avoid non-indexed XXL SQL queries *
1101008	Avoid non-SARGable queries *
1101010	Avoid NATURAL JOIN queries *
1101012	Specify column names instead of column numbers in ORDER BY clauses *
1101014	Avoid queries using old style join convention instead of ANSI-Standard joins *
1101016 Avoid Artifacts with too many parameters
1101018 Avoid using the GROUP BY clause
1101020 Avoid using quoted identifiers
1101022 Avoid Tables without Primary Key
1101024 Avoid using dynamic SQL in SQL Artifacts
1101026 Always define column names when inserting values *
1101028 Use MINUS or EXCEPT operator instead of NOT EXISTS and NOT IN subqueries *
*) Avoid SQL queries that no index can support was the previous name of that quality rule
* Applying not only for SQL Analyzer technology by also for all client technologies having client bookmarks with SQL Analyzer tables / views, with property "inferenceEngineRequests" (ID : 138788, description : "Requests found by the Inference Engine")  valued to a DML statement. Except Cobol language when it suffice to have client server bookmarks with SQL Analyzer tables / views.
Extractors
==========

- db2 : http://dba.stackexchange.com/questions/46771/how-to-use-db2look-to-get-the-ddl-of-sequence
- mysql : http://stackoverflow.com/questions/6597890/how-to-generate-ddl-for-all-tables-in-a-database-in-mysql
- mariaDB : http://www.heidisql.com/help.php?place=menuReadme, see SQL Export topic; https://confluence.castsoftware.com/display/DOCEXT/MariaDB+DDL+example+export+or+extraction
- postgreSQL : http://stackoverflow.com/questions/1884758/generate-ddl-programmatically-on-postgresql; https://confluence.castsoftware.com/display/DOCEXT/postgreSQL+schema+export+or+extraction+as+operator
- SQLite : http://sqlitebrowser.org/


Limitations
===========

General :
- all name resolving is considered as case insensitive : 
	may produce wrong links on case insensitive platform 'playing with case' : 2 different tables with the same name case insensitive will be both called
- procedure resolution do not handle overriding : when calling an overridden procedure, all overrides will be called
- Only ALTER TABLE ... ADD ... syntax is supported; all other syntax, like ALTER TABLE ... DELETE .. or ALTER TABLE ... DROP ... or ALTER TABLE ... MODIFY ... or ALTER TABLE .. RENAME ... etc ... are not supported.
	DROP  syntax is not supported, which means if you have CREATE ... followed by DROP ... only CREATE will be  considered. 
- For the QR 7156 Avoid Too Many Copy Pasted Artifacts we have total but no details

Oracle:
- no support of Synonyms

Specific to Microsoft and Sybase
- when the body o a stored procedure/function is not defined in a begin ... end block the analysis result is not guaranteed


Technical notes
===============

Perfs
-----

- max memory consumption on a 5M file is 16M with 2 passes (but twice slower) 
- 8 minutes for local schema
