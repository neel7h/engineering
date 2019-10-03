<?xml version="1.0" encoding="utf-8"?>
<Package PackName="PLUGIN_JEE_LOCAL" Type="SPECIFIC" Version="1.0.0.0" SupportedServer="ALL" Display="Refresh environment profiles" Description="" DatabaseKind="KB_LOCAL">
	<Include>
	</Include>
	<Exclude>
	</Exclude>
	<Install>
	</Install>
	<Update>
    </Update>
	<Refresh>
        <Step Type="PROC" File="clearProfiles.sql"></Step>
        <Step Type="PROC" File="local.sql"></Step>
	</Refresh>
	<Remove>
	</Remove>
</Package>