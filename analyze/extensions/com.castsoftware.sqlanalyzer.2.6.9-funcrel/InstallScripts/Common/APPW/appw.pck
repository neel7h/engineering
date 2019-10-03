<?xml version="1.0" encoding="utf-8"?>
<Package PackName="PLUGIN_SQLSCRIPT_APPW" Type="SPECIFIC" Version="1.0.0.1" SupportedServer="ALL" Display="APPW for SQLScript" Description="" DatabaseKind="KB_LOCAL">
	<Include>
	</Include>
	<Exclude>
	</Exclude>
	<Install>
	</Install>
	<Update>
    </Update>
	<Refresh>
        <Step Type="PROC" File="migrate_sap_procedures.sql"></Step>
	</Refresh>
	<Remove>
	</Remove>
</Package>