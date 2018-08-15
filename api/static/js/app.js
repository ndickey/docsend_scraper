'use strict';

const react_render = React.createElement

// requires downloadjs
function downloadFileNow(url, callbackfunc, file_data) {
    var data = new FormData();
    data.append( "json", JSON.stringify( file_data ) );
    
    return fetch(url, {method: "POST", body: data})
        .then(
            (resp) => {
                if (!resp.ok) {
                    return undefined
                } else {
                    callbackfunc()
                    return resp.blob()
                }
            }
        ).then(function(blob) {
            if (blob)
                download(blob, file_data.file_id + ".pdf")
        })
}


// requires downloadjs
function downloadFile(url, file_data, callbackfunc = () => {}, error_handler = () => {}) {
    if (url && file_data) {
        
        return fetch(`/now/${file_data.file_id}`, {method: "POST", body: JSON.stringify( file_data )}).then(
            (resp) => {
                if (!resp.ok)
                    throw resp

                callbackfunc()
                return resp.blob()
        }).then(
            (blob) => {
                if (blob)
                    download(blob, file_data.file_id + ".pdf")
        }).catch(
            (err) => {
                console.log(err)
                    return err.json()
                        .then(
                            (json_error) => {
                                error_handler(json_error.error, err)
                            }
                        ).catch(() => {
                            error_handler("unknown error", {})})
        })
    }
}

class FormGroup extends React.Component {

    render() {
        var children = []
        if (this.props.labeltext)
            children = [react_render('label', {className: "control-label col-sm-2", key: "cc_" + this.props.labeltext, htmlFor: this.props.for}, this.props.labeltext)]
        children.push(
            react_render('div', {key: "c_" + this.props.labeltext, className: this.props.className || "col-sm-10"}, this.props.children)
        )

        return react_render('div', {className: 'form-group has-feedback', key: this.props.labeltext}, children)
    }
}


const createFormElement = (inputElement, formGroupData) => {
    return react_render(FormGroup, formGroupData, inputElement)
}

const createScrapeButton = (onClickFunction) => {
    return createFormElement(
                react_render('button',
                    { onClick: onClickFunction, type: "submit", id:"submit", className: "btn btn-primary btn-med" },
                    'Scrape'
                ),
            {key: "submit_btn", className: "col-sm-offset-2 col-sm-10"}
        )
}

class SinglePageForm extends React.Component {

    constructor(props) {
        super(props)
        this.state = { download_msg: "" }
        this.form_ref = React.createRef()
    }

    updateMsg(url, buttonRef, loading = true, msg = null) {
        let msg_txt = msg || `Downloading from url: ${url} ...`;

        if (url && !loading) {
            msg_txt = msg || "Download complete."
        } else if (!url) {
            msg_txt = msg || "Invalid data"
        }

        this.setState((prevState) => {
          return {download_msg: msg_txt}
        })

        buttonRef.disabled = loading
    }

    onInputChange(term) {
        this.setState({ term });
    }
    onclick2(event) {
        return false;
    }
    onclick(event) {
        if (this.form_ref.current.checkValidity()) {
            event.preventDefault()
            event.persist()

            let formdata = this.form_ref.current
            if (formdata && formdata.url && formdata.url.value && formdata.emailad && formdata.emailpass) {
                let file_id = null
                var re = /https\:\/\/docsend.com\/view\/([A-Za-z0-9]+)/
                let matches = re.exec(formdata.url.value)
                if (matches.length >= 1) {
                    file_id = matches[1]
                }

                let download_data = {
                    url: formdata.url.value,
                    email: formdata.emailad.value,
                    password: formdata.emailpass.value,
                    file_id: file_id
                    }
                // console.log("sending", download_data)

                this.updateMsg(formdata.url.value, event.target)
                let callback = () => this.updateMsg(formdata.url.value, event.target, false)
                let on_error = (msg, response) => {
                    // console.log(response)
                    this.updateMsg(null, event.target, false, msg || "unknown error")
                }
                downloadFile('/now', download_data, callback, on_error)

            } else {
                this.updateMsg(null, event.target, false)
            }
        }
        return false;
    }

    render() {
        let input_defaults = {type: "text", className:"form-control"}

        let msg_box = react_render('div', null, this.state.download_msg)

        let link_pattern = "^https\:\/\/docsend\.com\/view\/[A-Za-z0-9]+$"

        let input1 = react_render('input', {...input_defaults, pattern: link_pattern, type: "url", id: "url", name: "url", placeholder: "enter link, i.e. https://docsend.com/view/p8jxsqr", required: true})
        let input2 = react_render('input', {...input_defaults, type: "email", id: "emailad", name: "emailad", placeholder: "enter email if needed ..."})
        let input3 = react_render('input', {...input_defaults, id: "emailpass", name: "emailpass", placeholder: "enter password if needed ..."})

        return react_render('form', {ref: this.form_ref, role: "form", className: "needs-validation form-horizontal" },
            [
                createFormElement(input1, {key: "url", for: "url", labeltext: "Link:"}),
                createFormElement(input2, {key: "emailad", for: "emailad", labeltext: "Email Address:"}),
                createFormElement(input3, {key: "pwd", for: "pwd", labeltext: "Docsend Password:"}),
                createFormElement(msg_box, {key: "txt", for: "txt", labeltext: "  "}),
                createScrapeButton(this.onclick.bind(this)),
            ]
          )
      }
  }

class ScraperApp extends React.Component {

    render() {
      return react_render(SinglePageForm)
    }

  }
