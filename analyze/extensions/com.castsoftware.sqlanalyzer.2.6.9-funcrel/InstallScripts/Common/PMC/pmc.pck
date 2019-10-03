<?xml version="1.0" encoding="utf-8"?>
<Package PackName="PLUGIN_SQLSCRIPT_PMC" Type="SPECIFIC" Version="1.0.0.0" SupportedServer="ALL" Display="Migrate CMS category description" Description="" DatabaseKind="KB_PMC">
	<Include>
	</Include>
	<Exclude>
	</Exclude>
	<Install>
	</Install>
	<Update>
    </Update>
	<Refresh>
        <Step Type="PROC" File="set_pmc.sql"></Step>
	</Refresh>
	<Remove>
	</Remove>
</Package>