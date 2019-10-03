<?xml version="1.0" encoding="utf-8"?>
<Package PackName="com.castsoftware.internal.platform.migration" Type="SPECIFIC" Version="1.0.0.0" SupportedServer="ALL" Display="Migrate GUIDs" Description="" DatabaseKind="KB_LOCAL">
	<Include>
		<PackName>CORE_APPW</PackName>
		<Version>1.0.0</Version>
	</Include>
	<Exclude>
	</Exclude>
	<Install>
	</Install>
	<Update>
    </Update>
	<Refresh>
		<Step Type="PROC" File="install_migration_of_extensions.sql"></Step>
	</Refresh>
	<Remove>
	</Remove>
</Package>