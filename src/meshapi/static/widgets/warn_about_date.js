$(document).ready(function($) {
    const getCurrentISODate = () => {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, '0'); // Months are 0-indexed
      const date = String(now.getDate()).padStart(2, '0');
      return `${year}-${month}-${date}`;
    };

    function submitAdminForm(saveAction) {
        const adminForm = document.querySelector('#content-main form');

        // Create a hidden input to simulate the button action
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = saveAction;
        hiddenInput.value = '1';
        adminForm.appendChild(hiddenInput);
        adminForm.submit();

        return true;
    }

    const saveButtons = $('.submit-row input[value*="Save"]');


    function hideWarning(){
        $('#dateMissingWarning').remove();
        saveButtons.each((i, button) => {
            $(button).removeClass("disabled-button");
        })
    }

    function showWarning(dateField, statusField, saveAction, dateType){
        const errorNotice = $("#dateMissingWarningTemplate").clone();
        errorNotice.prop("id", "dateMissingWarning");

        errorNotice.find("#saveCurrentDateButton").on("click", () => {
            dateField.val(getCurrentISODate())
            submitAdminForm(saveAction);
            return false;
        });

        errorNotice.find("#saveNoDateButton").on("click", () => {
            submitAdminForm(saveAction);
            return false;
        });

        errorNotice.find("#statusText").text(statusField.val());
        errorNotice.find("#dateTypeText").text(dateType);

        saveButtons.each((i, button) => {
            $(button).addClass("disabled-button");
        })

        errorNotice.insertBefore($('.submit-row').first())
    }

    $('#id_install_date').on("input", (e) => {
        hideWarning();
    });

    $('#id_abandon_date').on("input", (e) => {
        hideWarning();
    });

    $('#id_status').on("change", (e) => {
        hideWarning();
    });

    saveButtons.on('click', (e) => {
        const status = $('#id_status').val();
        const installDate = $('#id_install_date').val();
        const abandonDate = $('#id_abandon_date').val();

        $('.datetimeshortcuts a').on("click", (e) => {
            hideWarning();
        });

        if (status === "Active") {
            if (!installDate) {
                hideWarning();
                showWarning($("#id_install_date"), $('#id_status'), e.target.name, "Install")

                return false;
            }
        } else if (["Closed", "Inactive"].indexOf(status) !== -1){
            if (installDate && !abandonDate) {
                hideWarning();
                showWarning($("#id_abandon_date"), $('#id_status'), e.target.name, "Abandon")

                return false;
            }
        }

        return true;
    })
});
