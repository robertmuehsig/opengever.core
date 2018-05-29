var app = new Vue({
  template: '#sharing-form',
  el: '#sharing-view-vue-app',
  data: {
    userid: null,
    i18n: {},
    context_url:null,
    endpoint: null,
    available_roles: [],
    entries: [],
    inherit: null,
    authtoken: null,
    requester: null,
    principal_search: null,
  },

  beforeMount: function () {
    this.context_url = this.$el.attributes['data-contexturl'].value;
    this.portal_url = this.$el.attributes['data-portalurl'].value;
    this.endpoint = this.context_url + '/@sharing';
    this.i18n = JSON.parse(this.$el.attributes['data-i18n'].value);
    this.authtoken = this.$el.attributes['data-authtoken'].value;

    var requester = axios.create();
    requester.defaults.headers.common['Accept'] = 'application/json';
    requester.defaults.headers.common['Content-Type'] = 'application/json';
    this.requester = requester;
  },

  mounted: function () {
    this.fetchData();
  },

  methods: {
    errorMessage: function (){
      return this.messenger.shout([{
        'messageTitle': this.i18n.message_title,
        'message': this.i18n.message_not_saved, 'messageClass': 'error'}]);
    },

    fetchData: function () {
      // make sure IE 11 does not cache the fetch request
      var params = { _t: Date.now().toString()};
      this.requester.get(this.endpoint, { params: params }).then(function (response) {
        this.available_roles = response.data['available_roles'];
        this.entries = response.data['entries'];
        this.inherit = response.data['inherit'];

      }.bind(this));
    },

    toggle_checkbox: function (event, entry, role) {
      var checkbox = event.target;
      entry.roles[role] = checkbox.checked;

      // Mark entry as changed, by setting disabled to false, so it
      // gets not replaced when searching for other principal
      entry.disabled = false;
      // this.entries[principal].roles[role] = checkbox.checked;

    },

    search: function() {
      // make sure IE 11 does not cache the fetch request
      var params = { _t: Date.now().toString(), search: this.principal_search };
      this.requester.get(this.endpoint, { params: params }).then(function (response) {

        this.entries = Object.values(this.entries).filter(i => i.disabled == false);
        this.entries = this.entries.concat(
          response.data['entries'].filter(i => i.disabled != false));

        this.inherit = response.data['inherit'];

      }.bind(this));
    },

    save: function(event){
      payload = {
        entries: Object.values(this.entries),
        inherit: this.inherit };

      this.requester.post(this.endpoint, payload).then(function (response) {
        console.info('SAVED!!!');
      }.bind(this));
    },
  },
});
