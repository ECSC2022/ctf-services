// FAQ

document.querySelectorAll('.faq').forEach(faq => {
  const question = faq.querySelector('.faq-question')
  const answer = faq.querySelector('.faq-answer')

  function toggleVisibility () {
    faq.classList.toggle('faq-collapsed')
  }

  toggleVisibility()
  question.addEventListener('click', () => toggleVisibility())
})

document.querySelectorAll('input[data-only-show-when-active]').forEach(input => {
  const targetsSelector = input.dataset.onlyShowWhenActive
  const targets = document.querySelectorAll(targetsSelector)

  function toggleVisibility () {
    targets.forEach(target => {
      target.classList.toggle('hidden', !input.checked)
    })
  }

  const partners = document.querySelectorAll('input[name=\'' + input.name + '\']')
  partners.forEach(partner => {
    partner.addEventListener('change', () => toggleVisibility())
  })
  toggleVisibility()
})

document.querySelectorAll('input[type="file"][data-max-size]').forEach(input => {
  input.addEventListener('change', () => {
    const size = input.files[0].size
    const sizeUpdateTarget = document.querySelector(input.dataset.sizeUpdateTarget)
    const isInvalid = size > parseInt(input.dataset.maxSize)

    if (sizeUpdateTarget) {
      sizeUpdateTarget.classList.toggle("invalid", isInvalid)
      sizeUpdateTarget.value = (size / 1000).toFixed(1)
    }
    input.classList.toggle("invalid", isInvalid)
  })
})

document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', e => {
    const invalidObject = form.querySelector("input.invalid")
    if (invalidObject) {
      window.alert("Not all inputs are valid.")
      e.preventDefault()
      return false
    }
  })
})