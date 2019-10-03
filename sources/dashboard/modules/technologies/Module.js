/*
 This module provides functionalities that relates to technologies (e.g. listing of
 technologies or filtering of content based on technologies)
 */
(function() {
  define([], function(){

    TechnologyModule = function(facade){
      var _, module, t;
      _ = facade._;
      t = facade.i18n.t;

      var setProperStyling = function(selector, technologies){
        if (technologies.getSelected() === null){
          selector.$el.addClass('default');
        }
        else {
          selector.$el.removeClass('default');
        }
      };

      var createTechnologyFilter = function(options){
        var selector, technologies;
        technologies = options.technologies;
        selector = new facade.bootstrap.Selector({
          name: t('All Technologies'),
          data: technologies.asSelector({translate:t}),
          "class": 'right breadrumb-selector technology-selector',
          maxCharacters: 20
        });
        selector.on('selection', function(item){
          var previous = technologies.getSelected() || '-1';
          if (item === previous){
            return;
          }
          facade.bus.emit('filter', {technology:item});

        });
        setProperStyling(selector, technologies);
        facade.bus.on('breadcrumb',function(data){
          if (data.availableModules && data.availableModules.length === 0) {
            selector.disable();
          }
          else {
            selector.enable();
          }

          selector.enableOptions(data.availableTechnologies,t('The technology is not available in this context.'));
          // @moduleSelector.enableOptions(options.availableModules,"The module is not available for the selected criteria.")
        });
        facade.bus.on('technologyFilter:change',function(data){
          selector.selectValue(data.selectedTechnology || -1);
          setProperStyling(selector, technologies);
        });
        options.$el.html(selector.render());
        selector.$el.find('.cont .options').attr('data-before',t('Select a technology'))
        return selector;
      };

      module = {
        initialize:function(options){
          facade.bus.on('render:technologyFilter', this.renderTechnologyFilter, this);
          facade.bus.on('show', this.controlFilterDisplay, this);
        },
        renderTechnologyFilter:function(options){
          this.selector = createTechnologyFilter(_.extend({$el:facade.$('<div></div>')}, options, {technologies:facade.context.get('technologies')}));
        },
        controlFilterDisplay:function(options){
          if (!options){return;}
          if (!this.selector){return;}
          if ('quality-investigation' === options.pageId){
            this.selector.$el.show();
          }
          else {
            this.selector.$el.hide();
          }
        },
        destroy:function(){

        }
      };
      return module;
    };

    return TechnologyModule;
  });
}).call(this);
