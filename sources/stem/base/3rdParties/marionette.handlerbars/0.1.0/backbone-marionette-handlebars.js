(function() {
 
	Backbone.Marionette.Handlebars = {
		path: 'templates/',
		extension: '.handlebars'
	};
 
	Backbone.Marionette.TemplateCache.prototype.load = function() {
		if (this.compiledTemplate) 
		{
			return this.compiledTemplate;
		}
		if (Handlebars.templates && Handlebars.templates[this.templateId]) 
		{
			this.compiledTemplate = Handlebars.templates[this.templateId];
		}
		else 
		{
			var template = this.loadTemplate(this.templateId);
			this.compiledTemplate = this.compileTemplate(template);
		}
		return this.compiledTemplate;
	};
 
	Backbone.Marionette.TemplateCache.prototype.loadTemplate = function(templateId) {
		var template, templateUrl;
		try {
			template = Backbone.$(templateId).html();
		}
		catch (e) {
			
		}
		if (!template || template.length === 0) {
			templateUrl = Backbone.Marionette.Handlebars.path + templateId + Backbone.Marionette.Handlebars.extension;
			Backbone.$.ajax({
				url: templateUrl,
				success: function(data) { template = data; },
				async: false
			});
		}
		if (!template || template.length === 0){
			throw "NoTemplateError - Could not find template: '" + templateUrl + "'";
		}
		return template;
	};
 
	Backbone.Marionette.TemplateCache.prototype.compileTemplate = function(rawTemplate) 
	{
		return Handlebars.compile(rawTemplate);
	};
	
	Backbone.Marionette.Renderer.render = function (template, data) {

		var options;
		if (_.isObject(template) && !_.isFunction(template) && !_.isString(template)) 
		{
			options = _.omit(template, 'content');
			template = template.content;
		}
		
		if (!template) {
			var error = new Error("Cannot render the template since it's false, null or undefined.");
			error.name = "TemplateNotFoundError";
			throw error;
		}
		
		var templateFunc;
		if (typeof template === "function")
		{
			templateFunc = template;
		} 
		else 
		{
			templateFunc = Backbone.Marionette.TemplateCache.get(template);
		}

		return templateFunc(data, options);
		
	};
	
 
}());