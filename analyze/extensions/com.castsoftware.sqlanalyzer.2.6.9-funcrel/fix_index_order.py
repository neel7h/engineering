import cast_upgrade_1_5_22 # @UnusedImport @UnresolvedImport
from cast.application import ApplicationLevelExtension, LinkType # @UnresolvedImport
import logging



class IndexExtension(ApplicationLevelExtension):
    
    def end_application(self, application):
        """
        Set properties on rely on links from a property stored on the index
        
        cast.analyzer API is only able to save property on links from 8.1.0 and above
        So this technique is used for versions < 8.1.0 
        """
        logging.info("Start fixing order on index links")
        
        columns = application.objects().has_type('SQLScriptTableColumn')
        indexes = application.objects().has_type('SQLScript_IndexProperties')
        links = application.links().has_type(LinkType.relyon).has_caller(indexes).has_callee(columns)
        
        application.declare_property_ownership('CAST_WithOrder.order', links)
        
        # first load all indexes with their props 
        columns_by_index_id = {}
        for index in application.objects().has_type('SQLScript_IndexProperties').load_property('SQLScript_IndexProperties.columns'):
            
            columns = index.get_property('SQLScript_IndexProperties.columns')
            
            columns_by_index_id[index.id] = columns.split(';') if columns else None
        
        
        # now scan all the links and set the order property
        for link in links:
             
            column_name = link.get_callee().get_name()
            columns = columns_by_index_id[link.get_caller().id]
            
            link.save_property('CAST_WithOrder.order', columns.index(column_name)+1)

        logging.info("End fixing order on index links")            
