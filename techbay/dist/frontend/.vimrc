lsp.vuels.setup {
        on_attach = function(client)
            --[[
                Internal Vetur formatting is not supported out of the box

                This line below is required if you:
                    - want to format using Nvim's native `vim.lsp.buf.formatting**()`
                    - want to use Vetur's formatting config instead, e.g, settings.vetur.format {...}
            --]]
            client.resolved_capabilities.document_formatting = true
            on_attach(client)
        end,
        capabilities = capabilities,
        settings = {
            vetur = {
                completion = {
                    autoImport = true,
                    useScaffoldSnippets = true
                },
                format = {
                    defaultFormatter = {
                        html = "none",
                        js = "prettier",
                        ts = "prettier",
                    }
                },
                validation = {
                    template = true,
                    script = true,
                    style = true,
                    templateProps = true,
                    interpolation = true
                },
                experimental = {
                    templateInterpolationService = true
                }
            }
        },
        root_dir = util.root_pattern("header.php", "package.json", "style.css", 'webpack.config.js')
    }
