import cast_upgrade_1_5_22 # @UnusedImport @UnresolvedImport
from cast.application import ApplicationLevelExtension # @UnresolvedImport
import logging
import traceback
import logger


class CopyLengthOfTheLongestLine(ApplicationLevelExtension):
    
    def end_application(self, application):
        """
        copy lengthOfTheLongestLine property from SQLScript_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine 
            to CAST_MetricAssistant_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine
        """
        logging.debug("copy SQLScript_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine to CAST_MetricAssistant_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine")
        
        application.declare_property_ownership('CAST_MetricAssistant_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine',['SQlScriptMetricable'])

        try: 
            for o in application.objects().has_type('SQlScriptMetricable').load_property('SQLScript_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine'):
                valueOfLengthOfTheLongestLine = o.get_property('SQLScript_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine')
                if valueOfLengthOfTheLongestLine:
                    o.save_property('CAST_MetricAssistant_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine', valueOfLengthOfTheLongestLine)
        except:
            logger.warning('SQL-009', 'Internal issue during copy of SQLScript_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine to CAST_MetricAssistant_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine, because of %s ' % traceback.format_exc())              