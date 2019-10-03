<?xml version="1.0" encoding="utf-8"?>
<Package PackName="PLUGIN_JEE_SET" Type="SPECIFIC" Version="1.0.0.0" SupportedServer="ALL" Display="ADG Metric Tree for JEE" Description="" DatabaseKind="KB_LOCAL">
	<Include>
		<PackName>OBJSET</PackName>
		<Version>1.0.x</Version>
	</Include>
	<Exclude>
	</Exclude>
	<Install>
	</Install>
	<Update>
    </Update>
	<Refresh>
        <Step Type="PROC" File="set_methods_lambdas.sql"></Step>
        <Step Type="PROC" File="set_local.sql"></Step>
		<Step Type="DATA" File="set_data.xml" Model="set_tables.xml" Scope="OBJSETINIT"></Step>
		<Step Type="PROC" File="qualityRules.sql"></Step>
	</Refresh>
	<Remove>
	</Remove>
</Package>