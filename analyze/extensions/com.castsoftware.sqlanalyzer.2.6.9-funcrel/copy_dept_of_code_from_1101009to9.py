import cast_upgrade_1_5_22 # @UnusedImport @UnresolvedImport
from cast.application import ApplicationLevelExtension # @UnresolvedImport
import logging
import traceback
import logger



class CopyDepthOfCode (ApplicationLevelExtension):
    
    def end_application(self, application):
        """
        copy maxControlStatementsNestedLevels property from SQLScript_Metric_StatementsNestedLevels.maxControlStatementsNestedLevels (1101000, 28)
            to CAST_MetricAssistant_Metric_maxControlStatementsNestedLevels.maxControlStatementsNestedLevels (9, 1005) 
            which is open for all technologies, but results are nok for UA
        """
        logging.debug("copy SQLScript_Metric_StatementsNestedLevels.maxControlStatementsNestedLevels to CAST_MetricAssistant_Metric_maxControlStatementsNestedLevels.maxControlStatementsNestedLevels")
        
        application.declare_property_ownership('CAST_MetricAssistant_Metric_maxControlStatementsNestedLevels.maxControlStatementsNestedLevels',['SQlScriptMetricable'])

        try: 
            for o in application.objects().has_type('SQlScriptMetricable').load_property('SQLScript_Metric_StatementsNestedLevels.maxControlStatementsNestedLevels'):
                valueOfCodeDepth = o.get_property('SQLScript_Metric_StatementsNestedLevels.maxControlStatementsNestedLevels')
                if valueOfCodeDepth:
                    o.save_property('CAST_MetricAssistant_Metric_maxControlStatementsNestedLevels.maxControlStatementsNestedLevels', valueOfCodeDepth)
        except:
            logger.warning('SQL-008', 'Internal issue during copy of SQLScript_Metric_StatementsNestedLevels.maxControlStatementsNestedLevels to CAST_MetricAssistant_Metric_maxControlStatementsNestedLevels.maxControlStatementsNestedLevels, because of %s ' % traceback.format_exc())               