<?xml version="1.0" encoding="utf-8"?>
<Package PackName="PLUGIN_SQLSCRIPT_DSS" Type="SPECIFIC" Version="1.0.0.0" SupportedServer="ALL" Display="Migrate DSS category description" Description="" DatabaseKind="KB_CENTRAL">
	<Include>
	</Include>
	<Exclude>
	</Exclude>
	<Install>
	</Install>
	<Update>
    </Update>
	<Refresh>
        <Step Type="PROC" File="set_dss.sql"></Step>
	</Refresh>
	<Remove>
	</Remove>
</Package>