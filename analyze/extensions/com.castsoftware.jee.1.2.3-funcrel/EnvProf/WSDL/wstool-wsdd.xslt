<?xml version="1.0" encoding="ISO-8859-1"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/">
	<xsl:output method="xml" version="1.0" encoding="ISO-8859-1" indent="yes"/>
	<xsl:template match="/">
		<xsl:element name="webservices-impl">
			<xsl:for-each select="*[local-name() = 'deployment']/*[local-name() = 'service']">
				<xsl:element name="serviceImpl">
					<xsl:attribute name="name"/>
					<xsl:attribute name="wsdlFile"><xsl:value-of select="wsdlFile"/></xsl:attribute>
					<xsl:element name="portTypeImpl">
						<xsl:attribute name="name"><xsl:value-of select="*[local-name() = 'parameter'][@name='wsdlPortType']/@value"/></xsl:attribute>
						<xsl:attribute name="implClassFQName"><xsl:value-of select="*[local-name() = 'parameter'][@name = 'className']/@value"/></xsl:attribute>
						<xsl:element name="cwClassId">5040</xsl:element>
						<xsl:for-each select="*[local-name() = 'operation']">
							<xsl:element name="operationImpl">
								<xsl:attribute name="name"><xsl:value-of select="@name"/></xsl:attribute>
								<xsl:attribute name="implProcName"><xsl:value-of select="@name"/></xsl:attribute>
								<xsl:element name="cwClassId">5070</xsl:element>
							</xsl:element>
						</xsl:for-each>
					</xsl:element>
				</xsl:element>
			</xsl:for-each>
		</xsl:element>
	</xsl:template>
</xsl:stylesheet>
