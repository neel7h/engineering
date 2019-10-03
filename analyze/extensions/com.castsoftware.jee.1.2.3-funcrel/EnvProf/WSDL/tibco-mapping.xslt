<?xml version="1.0" encoding="iso-8859-1"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/">
	<xsl:output method="xml" version="1.0" encoding="ISO-8859-1" indent="yes"/>
<xsl:template match="/">
		<xsl:element name="webservices-impl">
		<xsl:if test="count(*[local-name() = 'definitions']/*[local-name() = 'service']) &gt; 0">
			<xsl:for-each select="*[local-name() = 'definitions']/*[local-name() = 'service']">
				<xsl:element name="serviceImpl">
					<xsl:attribute name="name"><xsl:value-of select="@name"/></xsl:attribute>
					<xsl:attribute name="wsdlFile"><xsl:value-of select="document('module-dir.xml')/module-dir/@wsdlFile" /></xsl:attribute>
					<xsl:if test="count(*[local-name() = 'port']) &gt; 0">
					<xsl:for-each select="*[local-name() = 'port']">
						<xsl:if test="contains(@binding, ':')">
							<xsl:variable name="bindingName" select="substring-after(@binding, ':')"/>
							<xsl:element name="portTypeImpl">
								<xsl:attribute name="name"><xsl:value-of select="substring-after(/*[local-name() = 'definitions']/*[local-name() = 'binding'][@name = $bindingName]/@type, ':')"/></xsl:attribute>
								<xsl:attribute name="implClassFQName"/>
								<xsl:if test="count(/*[local-name() = 'definitions']/*[local-name() = 'binding'][@name = $bindingName]/*[local-name() = 'operation']) &gt; 0">
								<xsl:for-each select="/*[local-name() = 'definitions']/*[local-name() = 'binding'][@name = $bindingName]/*[local-name() = 'operation']">
									<xsl:element name="operationImpl">
										<xsl:attribute name="name"><xsl:value-of select="@name"/></xsl:attribute>
										<xsl:attribute name="implProcName"><xsl:value-of select="substring-after(*[local-name() = 'operation']/@soapAction, '/')"/>.process</xsl:attribute>
										<!-- Tibco Process -->
										<xsl:element name="cwClassId">31030</xsl:element>
									</xsl:element>
								</xsl:for-each>
								</xsl:if>

							</xsl:element>
						</xsl:if>
						<xsl:if test="not(contains(@binding, ':'))">
							<xsl:variable name="bindingName" select="@binding"/>
							<xsl:element name="portTypeImpl">
								<xsl:attribute name="name"><xsl:value-of select="/*[local-name() = 'definitions']/*[local-name() = 'binding'][@name = $bindingName]/@type"/></xsl:attribute>
								<xsl:attribute name="implClassFQName"/>
								<xsl:if test="count(/*[local-name() = 'definitions']/*[local-name() = 'binding'][@name = $bindingName]/*[local-name() = 'operation']) &gt; 0">
								<xsl:for-each select="/*[local-name() = 'definitions']/*[local-name() = 'binding'][@name = $bindingName]/*[local-name() = 'operation']">
									<xsl:element name="operationImpl">
										<xsl:element name="operationImpl">
											<xsl:attribute name="name"><xsl:value-of select="@name"/></xsl:attribute>
											<xsl:attribute name="implProcName"><xsl:value-of select="substring-after(*[local-name() = 'operation']/@soapAction, '/')"/>.process</xsl:attribute>
											<!-- Tibco Process -->
											<xsl:element name="cwClassId">31030</xsl:element>
										</xsl:element>
									</xsl:element>
								</xsl:for-each>
								</xsl:if>

							</xsl:element>
						</xsl:if>
					</xsl:for-each>
					</xsl:if>

				</xsl:element>
			</xsl:for-each>
		</xsl:if>

		</xsl:element>
	</xsl:template>
</xsl:stylesheet>
