document.addEventListener("DOMContentLoaded", function () {
  const totals = {
      pwd: 0,
      remembering: 0,
      understanding: 0,
      applying: 0,
      analyzing: 0,
      evaluating: 0,
      creating: 0,
  };

  const inputs = document.querySelectorAll('input[name^="subtopic_"]');
  let debounceTimeout;

  inputs.forEach(input => {
      let previousValue = 0;

      input.addEventListener("input", function () {
          console.log("Input detected:", this.name); 

          const subtopicId = this.name.split('_')[2];
          const topicId = this.dataset.topicId;

          const rememberingValue = getValue(`subtopic_remembering_${subtopicId}`);
          const understandingValue = getValue(`subtopic_understanding_${subtopicId}`);
          const applyingValue = getValue(`subtopic_applying_${subtopicId}`);
          const analyzingValue = getValue(`subtopic_analyzing_${subtopicId}`);
          const evaluatingValue = getValue(`subtopic_evaluating_${subtopicId}`);
          const creatingValue = getValue(`subtopic_creating_${subtopicId}`);

          const subtopicTotal = rememberingValue + understandingValue + applyingValue + analyzingValue + evaluatingValue + creatingValue;
          document.querySelector(`input[name="subtopic_total_${subtopicId}"]`).value = subtopicTotal;

          updateTotalsForTopic(topicId);

          const currentValue = parseFloat(this.value) || 0;
          const change = currentValue - previousValue;
          previousValue = currentValue;

          updateTotals(topicId, this.name.split('_')[1], change);

          clearTimeout(debounceTimeout);
          debounceTimeout = setTimeout(calculateTotals, 30); 
      });
  });

  function getValue(name) {
      const input = document.querySelector(`input[name="${name}"]`);
      if (input) {
          return parseFloat(input.value) || 0;
      } else {
          console.log(`Input not found for name: ${name}`); 
          return 0;
      }
  }

  function updateTotalsForTopic(topicId) {
      updateRememberingTotal(topicId);
      updateUnderstandingTotal(topicId);
      updateApplyingTotal(topicId);
      updateAnalyzingTotal(topicId);
      updateEvaluatingTotal(topicId);
      updateCreatingTotal(topicId);
      updatePwdTotal(topicId);
      updateTopicTotal(topicId);
  }

  function calculateTotals() {
      console.log("Calculating totals..."); 
  
      const pwdCat = getValue('pwd_cat');
      console.log("PWD Cat:", pwdCat); 
      const rememberingCat = getValue('remembering_cat');
      const understandingCat = getValue('understanding_cat');
      const applyingCat = getValue('applying_cat');
      const analyzingCat = getValue('analyzing_cat');
      const evaluatingCat = getValue('evaluating_cat');
      const creatingCat = getValue('creating_cat');
  
      const total = rememberingCat + understandingCat + applyingCat + analyzingCat + evaluatingCat + creatingCat;
      console.log("Total:", total); 
  
      document.querySelector('input[name="pwd_cat_update"]').value = pwdCat;
      document.querySelector('input[name="remembering_cat"]').value = rememberingCat;
      document.querySelector('input[name="understanding_cat"]').value = understandingCat;
      document.querySelector('input[name="applying_cat"]').value = applyingCat;
      document.querySelector('input[name="analyzing_cat"]').value = analyzingCat;
      document.querySelector('input[name="evaluating_cat"]').value = evaluatingCat;
      document.querySelector('input[name="creating_cat"]').value = creatingCat;
  
      const totalsCatInput = document.querySelector('input[name="totals_cat"]');
      if (totalsCatInput) {
          totalsCatInput.value = total;
          console.log("Updated totals_cat:", total); 
      } else {
          console.log("Error: 'totals_cat' input not found!"); 
      }
  }
  

  function updateRememberingTotal(topicId) {
      updateTotalForCategory(topicId, 'subtopic_remembering_', 'remembering');
  }

  function updateUnderstandingTotal(topicId) {
      updateTotalForCategory(topicId, 'subtopic_understanding_', 'understanding');
  }

  function updateApplyingTotal(topicId) {
      updateTotalForCategory(topicId, 'subtopic_applying_', 'applying');
  }

  function updateAnalyzingTotal(topicId) {
      updateTotalForCategory(topicId, 'subtopic_analyzing_', 'analyzing');
  }

  function updateEvaluatingTotal(topicId) {
      updateTotalForCategory(topicId, 'subtopic_evaluating_', 'evaluating');
  }

  function updateCreatingTotal(topicId) {
      updateTotalForCategory(topicId, 'subtopic_creating_', 'creating');
  }

  function updateTotalForCategory(topicId, subtopicPrefix, category) {
      let total = 0;
      const inputs = document.querySelectorAll(`input[name^="${subtopicPrefix}"]`);

      inputs.forEach(input => {
          if (input.dataset.topicId == topicId) {
              total += parseFloat(input.value) || 0;
          }
      });

      const categoryInput = document.querySelector(`input[name="${category}_${topicId}"]`);
      if (categoryInput) {
          categoryInput.value = total;
      }
  }

  function updatePwdTotal(topicId) {
      let pwdTotal = 0;
      const pwdInputs = document.querySelectorAll(`input[name^="subtopic_pwd_"]`);

      pwdInputs.forEach(input => {
          if (input.dataset.topicId == topicId) {
              pwdTotal += parseFloat(input.value) || 0;
          }
      });

      const pwdInput = document.querySelector(`input[name="pwd_${topicId}"]`);
      if (pwdInput) {
          pwdInput.value = Number.isInteger(pwdTotal) ? pwdTotal : pwdTotal.toFixed(2);
      }
  }

  function updateTopicTotal(topicId) {
      let topicTotal = 0;
      const subtopicTotals = document.querySelectorAll(`input[name^="subtopic_total_"]`);

      subtopicTotals.forEach(input => {
          if (input.dataset.topicId == topicId) {
              topicTotal += parseFloat(input.value) || 0;
          }
      });

      const totalInput = document.querySelector(`input[name="total_${topicId}"]`);
      if (totalInput) {
          totalInput.value = topicTotal; 
      }
  }

  function updateTotals(topicId, category, change) {
      if (category in totals) {
          totals[category] += change;
          document.querySelector(`input[name="${category}_cat"]`).value = totals[category];
      }
  }
});
