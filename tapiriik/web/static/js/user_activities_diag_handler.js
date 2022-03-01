axios.defaults.headers.common['X-CSRFToken'] = document.querySelector('[name=csrfmiddlewaretoken]').value;

var app = new Vue({
    el: '#app',
    data() {
        return {
            editor,
            uid: uid,
            activities:[],
            beginDate: "",
            endDate: "",
        }
    },
    methods: {
        getActivitiesData(){
            axios.post("/diagnostics/api/user_activities", {"user": this.uid, "beginFilterDate": this.beginDate, "endFilterDate": this.endDate})
            .then(response => {this.editor.setValue(JSON.stringify(response.data, null, "\t"))})
            .catch(error => console.error(error))
        },
        changeBeginDate(e){
            this.beginDate = this.formatDate(e.detail.date)
        },
        changeEndDate(e){
            this.endDate = this.formatDate(e.detail.date)
        },
        formatDate(date){
            if (date.getTimezoneOffset() != 0){
                offset = date.getTimezoneOffset()
                epoch = date.getTime() / 1000
                date = new Date(0)
                date.setUTCSeconds(epoch-(offset*60))
            }
            splittedIsoDate = date.toISOString().split("T")[0].split("-")
            return splittedIsoDate[1] + "/" + splittedIsoDate[2] + "/" + splittedIsoDate[0]
        }
    },

    created(){
        this.beginDate = this.formatDate(new Date())
        this.endDate = this.formatDate(new Date())
        
    },
    mounted() {
        this.editor = CodeMirror.fromTextArea(document.getElementById('editor'), {
            theme: "rubyblue",
            mode: {
                name: 'javascript',
                json: !0
            },
            indentUnit: 4,
            lineNumbers: !0,
            autoClearEmptyLines: !0,
            matchBrackets: !0,
            lineNumbers: true,
            readOnly: true,
        });

        this.editor.setSize(null,600)
        this.editor.setValue("Loading ...")

        this.getActivitiesData()
    }
})