axios.defaults.headers.common['X-CSRFToken'] = document.querySelector('[name=csrfmiddlewaretoken]').value;

var app = new Vue({
    el: '#app',
    data() {
        return {
            editor,
            connectionId: "",
            partnerId: ""
        }
    },
    methods: {
        searchByPartnerId(){
            axios.post("/diagnostics/api/connections/search", {"partnerId": String(this.partnerId)})
            .then(response => {this.editor.setValue(JSON.stringify(response.data, null, "\t"))})
            .catch(error => {
                if (error.response.status < 500){
                    this.editor.setValue(JSON.stringify(error.response.data, null, "\t"))
                }
                console.error(error)
            })
        },
        searchByConnectionId(){
            axios.get("/diagnostics/api/connections/"+ this.connectionId)
            .then(response => {this.editor.setValue(JSON.stringify(response.data, null, "\t"))})
            .catch(error => {
                if (error.response.status < 500){
                    this.editor.setValue(JSON.stringify(error.response.data, null, "\t"))
                }
                console.error(error)
            })
        },
    },

    created(){
        
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
        this.editor.setValue("Please enter an ID and click on the corresponding search button")
    }
})