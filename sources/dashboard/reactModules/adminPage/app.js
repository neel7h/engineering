import { React } from 'stem.plugins/react'
import { ReactDOM } from 'stem.plugins/reactDom'
import { materialUI } from 'stem.plugins/materialUI'
import { PropTypes } from 'stem.plugins/react'

const Button = materialUI.Button;
const Toolbar = materialUI.Toolbar;
const AppBar = materialUI.AppBar;
const Typography = materialUI.Typography;
const withStyles = materialUI.withStyles;
// const {
//     Button,
//     colors,
//     createMuiTheme,
//     CssBaseline,
//     Dialog,
//     DialogActions,
//     DialogContent,
//     DialogContentText,
//     DialogTitle,
//     Icon,
//     Toolbar,
//     MuiThemeProvider,
//     PropTypes,
//     AppBar,
//     Typography,
//     IconButton,
//     MenuIcon,
//     withStyles,
// } = window['MaterialUI'];
const styles = theme => ({
    root: {
        textAlign: 'center',
        paddingTop: 0,
    },
    icon: {
        marginRight: theme.spacing.unit,
    },
});
class Index extends React.Component {

    render() {
        const { classes } = this.props;
        return (
                <div className={classes.root}>
                    <AppBar position="static">
                        <Toolbar>
                            <Typography variant="h6" color="inherit" className={classes.grow}>
                                News
                            </Typography>
                            <Button color="inherit">Login</Button>
                        </Toolbar>
                    </AppBar>
                </div>

        );
    }
}
const App = withStyles(styles)(Index);
ReactDOM.render(<App />, document.getElementById('component'));