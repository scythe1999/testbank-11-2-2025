function openConfirmationModal(id) {
  console.log('openConfirmationModal called with id:', id);
  const dialog = document.getElementById('deletequestionnaireconfirmation');
  dialog.showModal();

  document.getElementById('questionnaireIdToDelete').value = id;
}

function openConfirmationModalRestrict(id) {
  console.log('openConfirmationModalRestrict called with id:', id); 
  const dialog2 = document.getElementById('restrictquestionnaireconfirmation');
  dialog2.showModal();

  document.getElementById('questionnaireIdToRestrict').value = id;
}

function closeModal() {
  const dialog = document.getElementById('deletequestionnaireconfirmation');
  dialog.close();
}

function closeModalRestrict() {
  const dialog2 = document.getElementById('restrictquestionnaireconfirmation');
  dialog2.close();
}

function confirmDelete() {
  const id = document.getElementById('questionnaireIdToDelete').value;
  window.location.href = "{% url 'delete' 0 %}".replace('0', id);
}

function confirmRestrict() {
  const id = document.getElementById('questionnaireIdToRestrict').value;
  window.location.href = "{% url 'restrictquestion' 0 %}".replace('0', id);
}
