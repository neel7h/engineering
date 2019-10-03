import cast_upgrade_1_5_22 # @UnusedImport @UnresolvedImport
from cast.application import ApplicationLevelExtension # @UnresolvedImport
import logging
import traceback
import logger


class CopypreferUnionAllToUnion(ApplicationLevelExtension):
    
    def end_application(self, application):
        """
        copy details from SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnion (1101000, 16)
            to CAST_MetricAssistant_Metric_preferUnionAllToUnion.preferUnionAllToUnion (9, 1524) 
        and total from SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnionAnUnionAll (1101000, 17)
               and CAST_MetricAssistant_Metric_useOfUnionOrUnionAll.useOfUnionOrUnionAll (9, 1531)
            1101000 16 and 17 are computed by us, 9 is calculated by MA for UA
        """
        logging.debug("copy SQLScript_Metric_UnionAllInsteadOfUnion to CAST_MetricAssistant_Metric_useOfUnionOrUnionAll.useOfUnionOrUnionAll and CAST_MetricAssistant_Metric_preferUnionAllToUnion.preferUnionAllToUnion")
        
        application.declare_property_ownership('CAST_MetricAssistant_Metric_preferUnionAllToUnion.preferUnionAllToUnion',['SQlScriptMetricable'])
        application.declare_property_ownership('CAST_MetricAssistant_Metric_useOfUnionOrUnionAll.useOfUnionOrUnionAll',['SQlScriptMetricable'])   
     
        try: 
            for o in application.objects().has_type('SQlScriptMetricable').load_property('SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnion').load_property('CAST_MetricAssistant_Metric_preferUnionAllToUnion.preferUnionAllToUnion').load_property('SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnionAndUnionAll').load_property('CAST_MetricAssistant_Metric_useOfUnionOrUnionAll.useOfUnionOrUnionAll'):
                numberOfUnion = o.get_property('SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnion')
                preferUnion = o.get_property('CAST_MetricAssistant_Metric_preferUnionAllToUnion.preferUnionAllToUnion')
                numberOfUnionAndUnionAll = o.get_property('SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnionAndUnionAll')
                useOfUnionOrUnionAll = o.get_property('CAST_MetricAssistant_Metric_useOfUnionOrUnionAll.useOfUnionOrUnionAll')
                if numberOfUnion:o.save_property('CAST_MetricAssistant_Metric_preferUnionAllToUnion.preferUnionAllToUnion', numberOfUnion)
                if numberOfUnionAndUnionAll:o.save_property('CAST_MetricAssistant_Metric_useOfUnionOrUnionAll.useOfUnionOrUnionAll', numberOfUnionAndUnionAll)
                               
        except:
            logger.warning('SQL-012', 'Internal issue during copy of SQLScript_Metric_UnionAllInsteadOfUnion to CAST_MetricAssistant_Metric_useOfUnionOrUnionAll.useOfUnionOrUnionAll and CAST_MetricAssistant_Metric_preferUnionAllToUnion.preferUnionAllToUnion, because of %s ' % traceback.format_exc())               