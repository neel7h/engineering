/*
This module provides functionalities that relates to global application filtering (e.g. critical vs. all quality rules
related information)
*/
(function() {
  define([], function(){

    FilteringModule = function(facade){
      var _, module , t, Backbone, Handlebars;
      _ = facade._;
      t = facade.i18n.t;
      Backbone = facade.backbone;
      Handlebars = facade.Handlebars;


      var CriticalFilter = Backbone.View.extend({
        template:Handlebars.compile('<div class="filter">' +
        '<label class="switch"><input id="critical-filter" type="checkbox" {{#if isCritical}}checked{{/if}} /><div class="slider round"></div></label>' +
        '<span  class="switch-label critical-violation {{#if isCritical}}checked{{/if}}" title="{{t "Filter rules and violations by criticity"}}">{{t "Only critical violations"}}</span>' +
        '</div>' ),
        events:{
          'click .switch-label':'toggleSwitch',
          'change input':'onInputChange'
        },
        initialize:function(options){
          this.isCritical = facade.portal.getFilterSetting('criticalsOnly');
          facade.bus.on('global-filter-change:criticalsOnly',this.updateFilterState,this);
        },
        updateFilterState:function(options){
          var isCritical = facade.portal.getFilterSetting('criticalsOnly');
          if (this.isCritical !== isCritical){
            this.isCritical = facade.portal.getFilterSetting('criticalsOnly');
            this.render();
          }
        },
        toggleSwitch:function(event){
          $(event.target).prev('label').click();
        },
        onInputChange:function(event){
          this.isCritical = event.target.checked;
          this.$el.find('.switch-label').toggleClass('checked', this.isCritical);
          facade.portal.setFilterSetting('criticalsOnly', this.isCritical);
        },
        render:function(){
          this.$el.html(this.template({isCritical:this.isCritical}));
          return this.$el;
        }
      });

      var FilterArea = Backbone.View.extend({
        template:Handlebars.compile('<div class="filter-items">' +
        '</div><button class="close-button">Close</button>'),
        events:{
          'click .close-button':'close'
        },
        initialize:function(options){
          this.active = false;
        },
        close:function(){
          this.active = false;
          this.$el.parent().removeClass('global-filter-display');
        },
        open:function(){
          this.active = true;
          this.$el.parent().addClass('global-filter-display');
        },
        toggle:function(){
          if (this.active)
          return this.close();
          return this.open();
        },
        render:function(){
          this.$el.html(this.template({}));
          this.$el.find('.filter-items').append(new CriticalFilter().render());
          return this.$el;
        }
      });

      module = {
        initialize:function(options){
          this.view = new FilterArea({
            el: options.el
          });
          this.view.render();
          facade.bus.on('global-filter-display:toggle', this.view.toggle, this.view);
          facade.bus.on('data:store:reset', this.resetFilters, this);
        },
        resetFilters:function(options){
          if (options.key === 'filters'){
            facade.portal.resetFilters();
          }
        },
        destroy:function(){

        }
      };
      return module;
    };
    return FilteringModule;
  });
}).call(this);
