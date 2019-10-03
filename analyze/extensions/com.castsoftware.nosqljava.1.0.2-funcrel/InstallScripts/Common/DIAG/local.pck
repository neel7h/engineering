<?xml version="1.0" encoding="utf-8"?>
<Package PackName="PLUGIN_NoSQLJava_LOCAL" Type="SPECIFIC" Version="1.0.0.1" SupportedServer="ALL" Display="ADG Metric Tree for NoSQLJava" Description="" DatabaseKind="KB_LOCAL">
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
    </Refresh>
    <Remove>
    </Remove>
</Package>