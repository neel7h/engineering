<?xml version="1.0" encoding="utf-8"?>
<Package PackName="PLUGIN_SQLSCRIPT_LOCAL" Type="SPECIFIC" Version="1.0.0.1" SupportedServer="ALL" Display="ADG Metric Tree for SQLScript" Description="" DatabaseKind="KB_LOCAL">
	<Include>
	</Include>
	<Exclude>
	</Exclude>
	<Install>
	</Install>
	<Update>
    </Update>
	<Refresh>
        <Step Type="PROC" File="set_local.sql"></Step>
		<Step Type="DATA" File="set_data.xml" Model="set_tables.xml" Scope="OBJSETINIT"></Step>
        <Step Type="PROC" File="DIAG_ALL_ANA_SQL_ARTI_TOTAL.sql"></Step>
        <Step Type="PROC" File="DIAG_ARTIFAC_TOTAL.sql"></Step>
        <Step Type="PROC" File="DIA_SQL_ANALYZER_TECCPLEX004.sql"></Step>
        <Step Type="PROC" File="DSS_DIAG_SCOPE_1101014.sql"></Step>
        <Step Type="PROC" File="DSS_DIAG_SCOPE_1101025.sql"></Step>
        <Step Type="PROC" File="DSS_DIAG_SCOPE_1101042.sql"></Step>
        <Step Type="PROC" File="DSS_DIAG_SCOPE_1101044.sql"></Step>
        <Step Type="PROC" File="DSS_DIAG_SCOPE_1101046.sql"></Step>
        <Step Type="PROC" File="DSS_DIAG_SCOPE_1101048.sql"></Step>
        <Step Type="PROC" File="DSS_DIAG_SCOPE_1101050.sql"></Step>
	</Refresh>
	<Remove>
	</Remove>
</Package>