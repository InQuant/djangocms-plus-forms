$(function () {
    let form = $('form');
    let select = form.find('#id_field_type');
    let fieldset = form.find('.file_input--wrapper')

    if (select.val() !== "FileField" && select !== "ImageField") {
        fieldset.hide();
    }

    select.on('change',(e) => {
        let value = this.activeElement.value;
        if (value === "FileField" || value === "ImageField") {
            fieldset.show()
        } else {
            fieldset.hide()
        }
    });
});